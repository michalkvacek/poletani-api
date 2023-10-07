from datetime import datetime
from typing import List, Dict

from aiocache import cached
from lxml import etree
from lxml.etree import _ElementTree


class GPXParser:
    def __init__(self, file: str):
        self.file = file
        self.gpx = etree.parse(self.file)
        self.namespace = None
        self.precision_digits = 6
        self.set_namespace()

    def set_namespace(self):
        namespace = self.gpx.getroot().nsmap.get(None)
        self.namespace = {'gpx': namespace}

    def run_xpath(self, path: str):
        return self.gpx.xpath(path, namespaces=self.namespace)

    @cached()
    async def get_times(self):
        nodes = self.run_xpath("//gpx:trkpt/gpx:time")
        return [datetime.fromisoformat(node.text).astimezone() for node in nodes]

    @cached()
    async def get_coordinates(self) -> List[Dict[str, float]]:
        nodes = self.run_xpath("//gpx:trkpt")
        return [{"lat": float(node.attrib["lat"]), "lng": float(node.attrib['lon'])} for node in nodes]

    @cached()
    async def get_speed(self) -> List[int]:
        nodes = self.run_xpath("//gpx:speed")
        return [int(node.text) for node in nodes]

    @cached()
    async def get_magnetic_variation(self) -> List[int]:
        nodes = self.run_xpath("//gpx:magvar")
        return [int(node.text) for node in nodes]

    @cached()
    async def get_altitude(self) -> List[float]:
        nodes = self.run_xpath("//gpx:ele")
        return [float(node.text) for node in nodes]

    @cached()
    async def get_terrain_elevation(self) -> List[float]:
        nodes = self.run_xpath("//gpx:terrain_elevation")
        return [float(node.text) for node in nodes]

    @cached()
    async def get_max_speed(self):
        return max(await self.get_speed())

    @cached()
    async def get_avg_speed(self):
        speeds = await self.get_speed()
        return round(sum(speeds) / len(speeds), 2)

    @cached()
    async def get_max_altitude(self):
        return max(await self.get_altitude())

    @cached()
    async def get_avg_altitude(self):
        altitudes = await self.get_altitude()
        return round(sum(altitudes) / len(altitudes), 2)

    def add_terrain_elevation(self, points_with_elevation: List[Dict[str, float]]):
        track_points = self.run_xpath("//gpx:trkpt")
        # TODO: open elevation API umi jen presnost na 6 desetinnych mist!
        track_points_index = {(float(n.attrib['lat']), float(n.attrib['lon'])): n for n in track_points}

        for point_with_elevation in points_with_elevation:
            lat = point_with_elevation['lat']
            lng = point_with_elevation['lng']
            elevation = point_with_elevation['elevation']
            target_node = track_points_index.get((lat, lng))

            if target_node is None:
                continue

            extensions = target_node.find("./extensions", self.gpx.getroot().nsmap)
            extensions.append(etree.XML(f"<terrain_elevation>{elevation}</terrain_elevation>"))

        return self.gpx

    def write(self, tree: _ElementTree, output: str):
        print(f"ZAPISUJI DO {output}")
        tree.write(output)
