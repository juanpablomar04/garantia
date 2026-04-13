"""
dashboard_viewer.py
Lanzado como proceso independiente desde main.py para mostrar
el dashboard de MongoDB Charts usando pywebview.
Requiere: pip install pywebview
"""
import webview

DASHBOARD_URL = (
    "https://charts.mongodb.com/charts-project-0-jdpox"
    "/public/dashboards/63f79771-5123-4e3d-8e49-7f47128bc381"
)

if __name__ == "__main__":
    webview.create_window(
        "Dashboard — MongoDB Charts",
        DASHBOARD_URL,
        width=1280,
        height=800,
        resizable=True,
    )
    webview.start()
