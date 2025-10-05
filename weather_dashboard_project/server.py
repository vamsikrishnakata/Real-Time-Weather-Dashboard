import http.server
import socketserver
import urllib.parse
from weather_dashboard import get_weather
import mysql.connector

# MySQL connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ismav@4848",   # replace with your MySQL password
    database="weather_db"    # replace with your database name
)
cursor = conn.cursor()

PORT = 0  # automatically select a free port

class WeatherHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve CSS files
        if self.path.endswith(".css"):
            try:
                with open(self.path[1:], "r", encoding="utf-8") as f:
                    css_content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/css")
                self.end_headers()
                self.wfile.write(css_content.encode("utf-8"))
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        city = query.get("city", [None])[0]

        # DELETE ALL HISTORY
        if parsed_path.path == "/delete_all":
            cursor.execute("DELETE FROM search_history")
            conn.commit()
            self.send_response(302)
            self.send_header("Location", "/history")
            self.end_headers()
            return

        # DELETE SINGLE ENTRY
        if parsed_path.path.startswith("/delete?id="):
            id_to_delete = parsed_path.query.split("=")[1]
            cursor.execute("DELETE FROM search_history WHERE id=%s", (id_to_delete,))
            conn.commit()
            self.send_response(302)
            self.send_header("Location", "/history")
            self.end_headers()
            return

        # HISTORY PAGE
        if parsed_path.path == "/history":
            with open("history.html", "r", encoding="utf-8") as f:
                html_content = f.read()

            cursor.execute("SELECT * FROM search_history ORDER BY search_time DESC")
            rows = cursor.fetchall()

            if rows:
                tbody_html = ""
                for row in rows:
                    tbody_html += f"""
                    <tr>
                        <td>{row[0]}</td>
                        <td>{row[1]}</td>
                        <td>{row[2]}</td>
                        <td><a href="/delete?id={row[0]}"><button class="btn btn-danger">Delete</button></a></td>
                    </tr>
                    """
                html_content = html_content.replace(
                    '<!-- History rows will be injected here by server.py -->', tbody_html
                )
                html_content = html_content.replace(
                    'No history found.', ''
                )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
            return

        # DASHBOARD PAGE
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        if city:
            # Save search history to MySQL
            cursor.execute("INSERT INTO search_history (city, search_time) VALUES (%s, NOW())", (city,))
            conn.commit()

            # Get weather data
            weather = get_weather(city)
            if weather:
                html_content = html_content.replace("{{city}}", weather["city"])
                html_content = html_content.replace("{{temperature}}", str(weather["temperature"]))
                html_content = html_content.replace("{{humidity}}", str(weather["humidity"]))
                html_content = html_content.replace("{{wind_speed}}", str(weather["wind_speed"]))
                html_content = html_content.replace("{{description}}", weather["description"])
                html_content = html_content.replace("{{error_message}}", "")
            else:
                html_content = html_content.replace("{{city}}", "")
                html_content = html_content.replace("{{temperature}}", "")
                html_content = html_content.replace("{{humidity}}", "")
                html_content = html_content.replace("{{wind_speed}}", "")
                html_content = html_content.replace("{{description}}", "")
                html_content = html_content.replace("{{error_message}}", "City not found! Try again.")
        else:
            html_content = html_content.replace("{{city}}", "")
            html_content = html_content.replace("{{temperature}}", "")
            html_content = html_content.replace("{{humidity}}", "")
            html_content = html_content.replace("{{wind_speed}}", "")
            html_content = html_content.replace("{{description}}", "")
            html_content = html_content.replace("{{error_message}}", "")

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

with socketserver.TCPServer(("", PORT), WeatherHandler) as httpd:
    print(f"Serving at port {httpd.server_address[1]}")
    httpd.serve_forever()
