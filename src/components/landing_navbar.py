import flet as ft

def get_landing_appbar(page: ft.Page):
    return ft.AppBar(
        leading=ft.Container(
            content=ft.ElevatedButton(
                "Downloads",
                icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                color=ft.Colors.ON_PRIMARY,
                bgcolor=ft.Colors.PRIMARY,
                height=35,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: page.go("/offline")
            ),
            padding=ft.Padding.only(left=16),
            alignment=ft.Alignment.CENTER_LEFT,
        ),
        leading_width=180,
        actions=[
            ft.TextButton("Login",
                icon=ft.Icons.LOGIN,
                style=ft.ButtonStyle(color=ft.Colors.PRIMARY), # Themed equivalent of #009787
                on_click=lambda e: page.go("/")
            ),
            ft.ElevatedButton("Sign Up",
                icon=ft.Icons.PERSON_ADD_ALT_1,
                color=ft.Colors.ON_PRIMARY, # Themed equivalent of WHITE
                bgcolor=ft.Colors.PRIMARY, # Themed equivalent of #009787
                height=35,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: page.go("/signup")
            ),
        ],
        bgcolor=ft.Colors.ON_PRIMARY, # Themed equivalent of white
        toolbar_height=50
    )