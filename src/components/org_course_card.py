import flet as ft
import hashlib

def get_org_color(org_name: str) -> str:
    """Generate a consistent, vibrant color based on the organization name."""
    hash_val = int(hashlib.md5(org_name.encode('utf-8')).hexdigest(), 16)
    # List of premium, vibrant colors
    colors = [
        "#FF3B30", "#FF9500", "#FFCC00", "#4CD964", 
        "#5AC8FA", "#007AFF", "#5856D6", "#FF2D55",
        "#E56B6F", "#F4A261", "#2A9D8F", "#E76F51",
        "#219EBC", "#8ECAE6", "#118AB2", "#073B4C"
    ]
    return colors[hash_val % len(colors)]

def get_org_course_card(course_name: str, category: str, org_name: str, image_url: str, created_at: str, on_view_click=None) -> ft.Container:
    """Returns a premium card for an organisation course."""
    
    org_color = get_org_color(org_name)
    
    # View button matching the org color
    view_btn = ft.ElevatedButton(
        content=ft.Text("View Course", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
        bgcolor=org_color,
        expand=True,
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=0,
        ),
        on_click=on_view_click,
    )
    
    card = ft.Container(
        shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK), offset=ft.Offset(0, 4)),
        bgcolor=ft.Colors.SURFACE,
        border=ft.Border.all(2, org_color),
        border_radius=ft.BorderRadius.only(top_left=32, bottom_right=32, top_right=8, bottom_left=8),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        ink=True,
        scale=1.0,
        animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
        opacity=0,
        offset=ft.Offset(0, 0.1),
        animate_opacity=300,
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        content=ft.Column(
            spacing=0,
            controls=[
                # Image section
                ft.Container(
                    height=140,
                    image=ft.DecorationImage(
                        src=image_url if image_url else "assets/placeholder.png",
                        fit=ft.BoxFit.COVER,
                    ),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Container(
                                margin=10,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.SURFACE),
                                border_radius=8,
                                content=ft.Text(
                                    org_name,
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=org_color
                                )
                            )
                        ]
                    )
                ),
                # Content section
                ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                category or "Uncategorised",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.PRIMARY
                            ),
                            ft.Text(
                                course_name,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.Icons.BUSINESS_ROUNDED, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ft.Text(org_name, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                        ]
                                    ),
                                    ft.Text(created_at, size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                                ]
                            ),
                            ft.Container(height=8),
                            ft.Row(
                                controls=[view_btn]
                            )
                        ]
                    )
                )
            ]
        )
    )
    
    # Hover effect
    def on_hover(e):
        e.control.scale = 1.05 if e.data == "true" else 1.0
        e.control.shadow = ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.15, org_color), offset=ft.Offset(0, 6)) if e.data == "true" else ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK), offset=ft.Offset(0, 4))
        e.control.update()
        
    card.on_hover = on_hover
    return card