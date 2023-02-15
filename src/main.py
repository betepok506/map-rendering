from fastapi import FastAPI, Response
from fastapi_health import health
import os
import io
from src.glabalmaptiles import GlobalMercator
import logging
from PIL import Image, ImageDraw
from src.logger import LoggerFormating
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(LoggerFormating())
logger.addHandler(handler)
logger.propagate = False

app = FastAPI()
tileset = None


@app.on_event('startup')
def load_mbtiles():
    """
    Функция для реализации подключение к PostgreSql

    """
    pass
    # global tileset
    # FILE_NAME_MBTILES = os.path.join("./data", os.getenv("FILE_NAME_MBTILES"))
    # logger.info(f'Path loading Mbtiles: {FILE_NAME_MBTILES}.')
    # tileset = MbtileSet(mbtiles=FILE_NAME_MBTILES)
    # logger.info(f'Loading successfully')


def create_tiles(bboxes, tile_size: int = 256):
    """
    Функция для создания прозразного tile  и рисования на нем переданных полигонов

    Parameters
    ------------
    bboxes: `list`
        Массив пиксельных координат полигонов
    tile_size: `int`
        Размер создаваемого tile

    Returns
    ------------
    'np.array'
        Полученное изображение
    """
    img = Image.new('RGBA', (tile_size, tile_size), 'black')
    draw = ImageDraw.Draw(img)
    for bbox in bboxes:
        shape = [(bbox[0], bbox[1]), (bbox[2], bbox[3])]
        for ind in range(len(bbox)):
            draw.line((100, 200, 150, 300), fill=128)

        draw.rectangle(shape, outline="red", width=3)

    # img = img.convert("RGBA")
    datas = img.getdata()
    newData = []
    for item in datas:
        if item[0] == 0 and item[1] == 0 and item[2] == 0:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)

    img.putdata(newData)
    return img


@app.get("/auto/",
         response_class=Response,
         responses={
             200: {
                 "content": {"application/octet-stream": {}}
             }
         }
         )
async def root(z: int, x: int, y: int):
    """
    Функция по запрошенным координатам x, y и зуму z возвращает сгененированный tiles.
    Информация о объектах в tiles запрашивается из базы

    Parameters
    ------------
    z: `int`
        Zoom запрашиваемого tile
    x: `int`
        x координата запрашиваемого tile
    y: `int`
        y координата запрашиваемого tile

    Returns
    ------------
    `Response`
        Ответ сервера, содержащий bytearray массив изображения
    """
    zoom = z
    bboxes = get_boxes(x, y, zoom)
    bboxes = LatLon2Pixels(bboxes, x, y, zoom)
    img = create_tiles(bboxes, 256)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return Response(
        content=img_byte_arr,
        media_type="application/octet-stream",
    )


def LatLon2Pixels(bboxes, x, y, zoom):
    """
    Функция для преобразование координат широты и долготы в в пиксельные координаты в рамках одного изображения

    Parameters
    ------------
    bboxes: `list`
        Массив координат широты и долготы политгонов объектов
    x: `int`
        x координата запрашиваемого tile
    y: `int`
        y координата запрашиваемого tile
    zoom: `int`
        Zoom запрашиваемого tile

    Returns
    ------------
    `list`
        Массив пиксельных координат полигонов в рамках одного tile
    """
    glm = GlobalMercator()
    bboxes_pixel = []
    meters = glm.TileBounds(x, y, zoom)
    left_x, left_y = glm.MetersToPixels(meters[0], meters[1] * -1, zoom)
    for bbox in bboxes:
        x1_meters, y1_meters = glm.LatLonToMeters(bbox[0], bbox[1])
        x1, y1 = glm.MetersToPixels(x1_meters, y1_meters, zoom)
        x2_meters, y2_meters = glm.LatLonToMeters(bbox[2], bbox[3])
        x2, y2 = glm.MetersToPixels(x2_meters, y2_meters, zoom)

        bboxes_pixel.append(list(map(int, [x1 - left_x, abs(y1 - left_y), x2 - left_x, abs(y2 - left_y)])))

    return bboxes_pixel


def get_boxes(x, y, zoom):
    """
    Функция для получения bbox, лежащих внутри tile
    Вдальнейшем будет заменена на скрипт внутри PostgreSQL

    Parameters
    ------------
    x: `int`
        x координата запрашиваемого tile
    y: `int`
        y координата запрашиваемого tile
    zoom: `int`
        Zoom запрашиваемого tile

    Returns
    ------------
    `list`
        Массив координат bboxes, лежащих внутри tile
    """
    print(f"X {x} {y} {zoom}")
    """Находит BBoxes в tiles"""
    car_bboxes = [
        [54.18632391751572, 45.177304744720466, 54.18631842427248, 45.17738252878187],
        [54.1863247022647, 45.17730206251144, 54.18630351403713, 45.17737850546836],

        [54.18468, 45.17661, 54.18466, 45.17668],
        [54.18465, 45.17665, 54.18463, 45.17673],
        [54.18467, 45.17683, 54.18465, 45.1769],
        [54.18472, 45.17717, 54.18468, 45.17723],
        [54.18463, 45.17707, 54.18461, 45.17713],
    ]
    if zoom < 19:
        return []

    glm = GlobalMercator()
    poly = [abs(x) for x in glm.TileBounds(x, y, zoom)]
    left_x, left_y = glm.MetersToPixels(poly[0], poly[1], zoom)
    right_x, right_y = glm.MetersToPixels(poly[2], poly[3], zoom)
    print(f"Left x {left_x} left_ y {left_y}")
    print(f"right_x {right_x} right_y {right_y}")
    polygon = Polygon(((left_x, left_y),
                       (left_x, right_y),
                       (right_x, right_y),
                       (right_x, left_y),
                       (left_x, left_y)))  # create polygon

    # polygon = Polygon(((poly[0], poly[1]),
    #                    (poly[0], poly[3]),
    #                    (poly[2], poly[3]),
    #                    (poly[2], poly[1]),
    #                    (poly[0], poly[1])))  # create polygon

    # polygon = Polygon([[poly[1], poly[0]],
    #                    [poly[3], poly[0]],
    #                    [poly[3], poly[2]],
    #                    [poly[1], poly[2]],
    #                    [poly[1], poly[0]]])  # create polygon
    # print(polygon)
    # bbPath = mplPath.Path(np.array([[poly[0], poly[1]],
    #                                 [poly[2], poly[3]]]))
    result = []
    # result.append([abs(x) for x in glm.TileLatLonBounds(x, y, zoom)])
    # result.append([54.18632391751572, 45.177304744720466, 54.18631842427248, 45.17738252878187])
    for cur_bbox in car_bboxes:
        meters_x, meters_y = glm.LatLonToMeters(cur_bbox[0], cur_bbox[1])
        x__, y__ = glm.MetersToPixels(meters_x, meters_y, zoom)
        print(x__, y__)
        point = Point(x__, y__)  # create point
        # print(polygon.contains(point))  # check if polygon contains point
        # print(polygon.area)  # check if polygon contains point
        if point.within(polygon):  # check if a point is in the polygon
            result.append(cur_bbox)
        # if bbPath.contains_point((cur_bbox[0], cur_bbox[1])):
        #     result.append(cur_bbox)
        #     print("gg")
    # print(result)
    return result


def check_ready():
    return tileset is not None


async def success_handler(**kwargs):
    return Response(status_code=200, content='Mbtiles is loaded')


async def failure_handler(**kwargs):
    return Response(status_code=500, content='Mbtiles is not loaded')


app.add_api_route('/health', health([check_ready],
                                    success_handler=success_handler,
                                    failure_handler=failure_handler))
