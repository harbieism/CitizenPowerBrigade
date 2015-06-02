from powermap.models import PowerCar
from django.contrib.auth.models import User
from rest_framework import viewsets
from pttp.powermap.serializers import PowerCarSerializer, UserSerializer
from django.shortcuts import render


class PowerCarViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cars to be viewed or edited.
    """
    queryset = PowerCar.objects.all()
    serializer_class = PowerCarSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


def index(request):
    return render(request, 'powermap/index.html', {})
