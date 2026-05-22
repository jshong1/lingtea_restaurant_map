from geopy.geocoders import ArcGIS

geolocator = ArcGIS()
location = geolocator.geocode("선릉로90길 48, 강남구, 서울")
if location:
    print(f"ArcGIS: {location.latitude}, {location.longitude}")
else:
    print("ArcGIS Not found")

location2 = geolocator.geocode("대치동 890-27, 강남구, 서울")
if location2:
    print(f"ArcGIS: {location2.latitude}, {location2.longitude}")
else:
    print("ArcGIS Not found")
