<img src="http://www.rbasedservices.com/wp-content/uploads/2020/06/cropped-RBS_LOGO.png" style="zoom:15%;" />

# Bihar Industrial Area Development Authority (BIADA)

DIS Source Code made with Dash/Flask framework by RBased Services Pvt. Ltd.

> **This repository is private and should be accessed only by authorized developers from RBased Services Pvt. Ltd.**



## Initial Setup

Install required python libraries.

```bash
pip install -r requirements.txt
```

Run the app.

```bash
python app.py
```



## API Calls

To add a new user,

```bash
/api/createuser?username=<username>&password=<password>&key=<key>
```

To show all user names,

```bash
/api/showusers?key=<key>
```

To show all user names and passwords,

```bash
/api/showusers?key=<key>&showpass=true
```

To delete an user,

```bash
/api/dropuser?username=<username>&key=<key>
```



## File bindings

The location and format of the files are of paramount importance to run the application. The description of files and the required formats are specified below.

#### Plots Boundary (GeoJSON)

The plot boundary shapefile is located in `json/plot.geojson`. The GeoJSON can simply be created by opening the shapefile in QGIS and then saved as GeoJSON. 

> **Important** - The GeoJSON file should have `UID`, `Plt_No` (Plot Number) and `Area` as attributes.

#### Dehradun District Boundary (GeoJSON)

The Dehradun district boundary shapefile is located in `json/uk_district.geojson`. The GeoJSON can simply be created by opening the shapefile in QGIS and then saved as GeoJSON. 

#### Choropleth Color Scheme

The color scheme of different Plot Status classes can be defined in the CSV file located at `support_files/ choropleth_color_scheme.csv`. The CSV file should have two columns named `Class` and `Color`. 

> **Important** - The Colors should be defined as HEX Code. An easy to use color picker can be found [here](https://g.co/kgs/iwb99v).

