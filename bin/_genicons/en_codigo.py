# -*- coding: latin-1 -*-
import os

# import shutil


def leeFormato():
    with open("Formatos.tema") as f:
        st = set()
        for linea in f:
            linea = linea.strip()
            if linea and not linea.strip().startswith("#"):
                nombre, folder, png = linea.split(" ")
                st.add(nombre)
    return st


def leeCodigo(li, carpeta):
    for x in os.listdir(carpeta):
        x = os.path.join(carpeta, x)
        if x == "Iconos.py":
            continue
        if os.path.isdir(x):
            leeCodigo(li, x)
        elif x.endswith(".py"):
            with open(x) as f:
                for linea in f:
                    if "Iconos." in linea and not linea.startswith("from Code.QT ") and "()" in linea:
                        l = linea.split("Iconos.")
                        for t in l[1:]:
                            lp = t.split("(")[0]
                            if lp.startswith("pm"):
                                lp = lp[2:]
                            li.add(lp)
                            # print x, lp


stFormato = leeFormato()

sd = """Excavator
Elephant
Hippo
Rabbit
Panda
FireTruck
BoatEquipment
Airplane
AirAmbulance
Cat
Tiger
Bee
Rooster
ForkliftTruckLoaded
Eagle
Moose
Dog
Deer
Sheep
Horse
Bat
Car
Mouse
Frog
Rhino
Turkey
DieselLocomotiveBoxcar
Giraffe
Duck
Container
Crab
CarTrailer
TowTruck
TractorUnit
QuadBike
Cabriolet
Wheelchair
ContainerLoader
Fox
Locomotora
Bird
RecoveryTruck
Fish
SubwayTrain
Lorry
Bulldog
MixerTruck
Ant
Bear
PoliceCar
Cow
Truck
Ambulance
CargoShip
Owl
Alligator
TouringMotorcycle
Shark
Pig
Butterfly
Turtle
Crocodile
Insect
TruckMountedCrane
Gorilla
ExecutiveCar
Chicken"""

# print stFormato
stIco = set()
leeCodigo(stIco, "../../Program/Code")
# print stIco

for gg in sd.split("\n"):
    stIco.add(gg)


stq = set()
for xf in stFormato:
    if xf not in stIco:
        stq.add(xf)

with open("Formatos.tema1", "wb") as q, open("Formatos.tema", "rb") as f:
    for linea in f:
        if linea.strip():
            li = linea.split(" ")
            if li[0] not in stq:
                q.write(linea)
        else:
            q.write(linea)
