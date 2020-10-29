import os
import sys
import geoip2.database



'''取得當下目錄'''
current_path = os.path.abspath(__file__)


def getcountry(__Ip):
    '''取得city mmdb路徑'''
    citymmdb_path=os.path.join(os.path.abspath(os.path.dirname(current_path) + os.path.sep ),'GeoIP2-City.mmdb')

    reader = geoip2.database.Reader(citymmdb_path)
    response = reader.city(__Ip)
    country = response.country.names["en"]
    city = response.city.name
    latitude = response.location.latitude
    longitude = response.location.longitude
    reader.close()
    return country,city,latitude,longitude

