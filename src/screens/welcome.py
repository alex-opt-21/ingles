import flet as ft


def welcome_screen(page):

    page.bgcolor = "#F7F9FF"

    page.add(
        ft.Column(
            [
                ft.Container(height=60),

                ft.Text(
                    "Bright English",
                    size=40,
                    weight=ft.FontWeight.BOLD,
                    color="#1B2E5B"
                ),

                ft.Container(height=10),

                ft.Text(
                    "Learn English. Speak with confidence.",
                    size=16,
                    color="#52627A",
                    text_align=ft.TextAlign.CENTER
                ),

                ft.Container(height=50),

                ft.ElevatedButton(
                    text="Get Started",
                    width=280,
                    height=55
                ),

                ft.Container(height=15),

                ft.OutlinedButton(
                    text="Login",
                    width=280,
                    height=55
                ),

            ],

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )
    )
