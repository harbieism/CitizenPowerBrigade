from powermap.forms import (
    HelpNoteModelForm,
    NextLocationForm,
    PowerCarModelForm,
    UserModelForm
)

from powermap.models import PowerCar, HelpNote, Diagnostic

from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.sessions.models import Session
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from twilio_utils import send_alerts


from rest_framework import viewsets, status
from rest_framework.decorators import list_route, detail_route
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly,
    IsAuthenticated
)
from rest_framework.response import Response

from custom_permissions import IsAdminOrCarOwner, WriteOnlyOrUser
from serializers import (
    PowerCarSerializer,
    PowerCarMinSerializer,
    UserSerializer,
    HelpNoteSerializer,
    DiagnosticSerializer
)

import json


class DiagnosticViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows for CRUD operations
    on Diagnostics.
    """
    permissions_classes = (IsAuthenticated,)
    queryset = Diagnostic.objects.all()
    serializer_class = DiagnosticSerializer


class PowerCarViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cars to be viewed or edited.
    """
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = []

    # Build list of user IDs from session query.
    for session in sessions:
        data = session.get_decoded()
        uid_list.append(data.get('_auth_user_id', None))
    users = User.objects.filter(id__in=uid_list)
    queryset = PowerCar.objects.filter(owner__in=users)
    serializer_class = PowerCarSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @list_route()
    def other_active_cars(self, request):
        """
        API endpoint that allows all active cars but the users to be viewed.
        """
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        uid_list = []

        # Build list of user IDs from session query.
        for session in sessions:
            data = session.get_decoded()
            uid_list.append(data.get('_auth_user_id', None))
        uid = request.user.id
        users = User.objects.filter(id__in=uid_list).exclude(id=uid)
        queryset = PowerCar.objects.filter(owner__in=users, active=True)
        serializer = PowerCarMinSerializer(queryset, many=True)
        content = {"car_data": serializer.data}
        content["arrived_info"] = {}
        for each_car in queryset:
            content["arrived_info"][each_car.id] = each_car.at_next_location()
        return JsonResponse(content)

    @list_route()
    def other_car_coords(self, request):
        """
        API endpoint that returns a dictionary of car coordinates keyed to
        their IDs.
        """
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        uid_list = []

        # Build list of user IDs from session query.
        for session in sessions:
            data = session.get_decoded()
            uid_list.append(data.get('_auth_user_id', None))
        uid = request.user.id
        users = User.objects.filter(id__in=uid_list).exclude(id=uid)
        queryset = PowerCar.objects.filter(owner__in=users, active=True)
        serializer = PowerCarMinSerializer(queryset, many=True)
        content = {}
        for each_car in serializer.data["features"]:
            content[each_car["id"]] = {
                "arrived": PowerCar.objects.get(
                    id=each_car["id"]
                ).at_next_location(),
                "current_location": each_car["geometry"],
                "next_location": each_car["properties"]["next_location"]
            }
        return JsonResponse(content)

    @list_route()
    def get_user_car(self, request):
        car = PowerCar.objects.get(owner=request.user)
        serializer = PowerCarMinSerializer(car)
        content = {"car_data": serializer.data}
        content["arrived"] = car.at_next_location()
        return JsonResponse(content)

    @detail_route(methods=['post'], permission_classes=[IsAdminOrCarOwner])
    def update_current_location(self, request, pk=None):
        """
        Allows a car to update its current location via a POST request.
        """
        if request.method == 'POST':
            try:
                car = PowerCar.objects.get(id=pk)
            except PowerCar.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            serializer = PowerCarSerializer(
                car,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

    @detail_route(methods=['post'], permission_classes=[IsAdminOrCarOwner])
    def change_next_location(self, request, pk=None):
        """
        A route to change the next_location of a PowerCar,
        as well as its ETA and time at current location.
        """
        car = get_object_or_404(PowerCar, id=pk)
        partial_update = {}
        now = timezone.now().tzinfo
        partial_update["next_location"] = Point(
            float(request.data.get("lng")),
            float(request.data.get("lat"))
        )
        arrival_time = request.data.get("arrival_time")
        arrival_time = datetime.strptime(arrival_time, "%y-%m-%d %H:%M")
        partial_update["eta"] = arrival_time.replace(tzinfo=now)
        stay_time = request.data.get("stay_time")
        stay_time = datetime.strptime(stay_time, "%y-%m-%d %H:%M")
        stay_time = stay_time.replace(tzinfo=now)
        partial_update["current_location_until"] = stay_time
        serializer = PowerCarSerializer(car, data=partial_update, partial=True)
        if serializer.is_valid():
            serializer.save()
            alert_notes = HelpNote.objects.filter(
                location__distance_lte=(car.next_location, 500)
            )
            alert_notes = alert_notes.exclude(phone_number="")
            alert_numbers = [notes.phone_number for notes in alert_notes]
            send_alerts(alert_numbers, car, "SetDestination")

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HelpNoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows help notes to be viewed or edited.
    """
    permission_classes = (WriteOnlyOrUser,)
    queryset = HelpNote.objects.all()
    serializer_class = HelpNoteSerializer

    @list_route(methods=['get'])
    def update_notes(self, request):
        response_dict = {}
        for each in HelpNote.objects.all():
            response_dict[str(each.id)] = True
        return JsonResponse(response_dict)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


def index(request):
    if request.method == 'POST':
        form = HelpNoteModelForm(request.POST)
        if form.is_valid():
            form.save()
            form = HelpNoteModelForm()
            return redirect('index')
    form = HelpNoteModelForm()
    if request.user.is_staff:
        return render(
            request,
            'powermap/index.html',
            {"form": form, "authuser": False, "admin": True})
    if request.user.is_authenticated():
        car = get_object_or_404(PowerCar, owner=request.user)
        activity = car.active
        return render(
            request,
            'powermap/index.html',
            {"form": form, "authuser": True, "activity": activity}
        )
    else:
        return render(
            request,
            'powermap/index.html',
            {"form": form, "authuser": False}
        )


def car_popup(request, **kwargs):
    car_id = kwargs['car_id']
    car = PowerCar.objects.get(id=car_id)
    context = {
        "name": car.name,
        "vehicle_description": car.vehicle_description,
        "license_plate": car.license_plate, "owner": car.owner
    }
    return render(request, 'powermap/car_popup.html', context)


def note_popup(request, **kwargs):
    if request.user.is_authenticated():
        help_note_id = kwargs['note_id']
        note = HelpNote.objects.get(id=help_note_id)
        context = {
            "address": note.address, "message": note.message,
            "creator": note.creator
        }
        return render(request, 'powermap/note_popup.html', context)
    raise Http404


def logout_view(request):
    logout(request)
    return redirect('index')


def login_user(request):
    logout(request)
    username = password = ''
    if request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('index')
    form = HelpNoteModelForm()
    return render(request, 'powermap/login.html', {'form': form})


def set_active(request, *args, **kwargs):
    response_data = {}
    if request.method == "POST":
        identified_user = get_object_or_404(User, pk=request.user.id)
        user_car = get_object_or_404(PowerCar, owner=identified_user)
        car_id = kwargs.get('car_id')
        if user_car.id != int(car_id):
            return HttpResponse(
                json.dumps({"result": "Cars don't match"}),
                content_type="application/json"
            )
        user_car.active = not user_car.active
        user_car.save()
        response_data['result'] = 'Change active successfully'
        response_data['state'] = user_car.active
        response_data['car_id'] = car_id

        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )
    else:
        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )


def next_location_popup(request, *args, **kwargs):
    if request.method == "GET":
        form = NextLocationForm()
        return render(
            request,
            "powermap/next_location_popup.html",
            {"form": form}
        )
    if request.method == "POST":
        identified_user = request.user
        car = get_object_or_404(PowerCar, owner=identified_user)
        response_data = {}
        lat = request.POST.get("lat")
        lng = request.POST.get("lng")
        now = timezone.now().tzinfo
        new_point = Point(float(lng), float(lat))
        car.next_location = new_point
        arrival_time = request.POST.get("arrival_time")
        arrival_time = datetime.strptime(arrival_time, "%y-%m-%d %H:%M")
        arrival_time = arrival_time.replace(tzinfo=now)
        car.eta = arrival_time
        stay_time = request.POST.get("stay_time")
        stay_time = datetime.strptime(stay_time, "%y-%m-%d %H:%M")
        stay_time = stay_time.replace(tzinfo=now)
        car.current_location_until = stay_time
        alert_notes = HelpNote.objects.filter(
            location__distance_lte=(car.next_location, 500)
        )
        alert_notes = alert_notes.exclude(phone_number="")
        alert_numbers = [notes.phone_number for notes in alert_notes]
        send_alerts(alert_numbers, car, "SetDestination")
        car.save()

        response_data['result'] = 'Change next successfully'

        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )


def register_success(request):
    return render(request, "powermap/register_success.html")


def register_car(request, *args, **kwargs):
    if request.method == "GET":
        user_form = UserModelForm()
        car_form = PowerCarModelForm()
        context = {
            "user_form": user_form,
            "car_form": car_form
        }
        return render(request, 'powermap/register_car.html', context)
    if request.method == "POST":
        user_form = UserModelForm(request.POST)
        car_form = PowerCarModelForm(request.POST)
        if user_form.is_valid() and car_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            car = car_form.save(commit=False)
            car.owner = user
            car.current_location = Point(45.0, 45.0)
            car.next_location = Point(45.0, 45.0)
            car.target_location = Point(45.0, 45.0)
            car.save()
            return redirect("register_success")
        else:
            context = {
                "user_form": user_form,
                "car_form": car_form
            }
            return render(request, 'powermap/register_car.html', context)
