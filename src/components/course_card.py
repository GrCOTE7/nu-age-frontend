import flet as ft


def get_course_card(
    course_title: str,
    course_category: str,
    course_author: str,
    image_url: str | None = None,
    created_at: str | None = None,
    on_view_click=None,
):
    # ── cover ─────────────────────────────────────────────────────────────────
    if image_url:
        cover = ft.Container(
            height=140,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border_radius=ft.BorderRadius.only(top_left=32, top_right=8),
            content=ft.Image(
                src=image_url,
                fit=ft.BoxFit.COVER,
                width=float("inf"),
                placeholder_src="/placeholder.png",
                placeholder_fit=ft.BoxFit.COVER,
                placeholder_fade_out_animation=ft.Animation(
                    duration=ft.Duration(milliseconds=900),
                    curve=ft.AnimationCurve.EASE_OUT,
                ),
                fade_in_animation=ft.Animation(
                    duration=ft.Duration(milliseconds=700),
                    curve=ft.AnimationCurve.EASE_IN_OUT,
                ),
            ),
        )
    else:
        cover = ft.Container(
            height=140,
            bgcolor=ft.Colors.INDIGO_300,
            gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_LEFT,
                        end=ft.Alignment.BOTTOM_RIGHT,
                        colors=[ft.Colors.PURPLE_200, ft.Colors.INDIGO_200]
                    ),
            border_radius=ft.BorderRadius.only(top_left=32, top_right=8),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, size=44,
                            color=ft.Colors.ON_PRIMARY),
        )

    # ── category pill ─────────────────────────────────────────────────────────
    category_pill = ft.Container(
        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
        bgcolor=ft.Colors.SURFACE,
        border_radius=10,
        content=ft.Text(
            course_category or "General",
            size=10,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.PRIMARY,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    )

    # ── meta row ──────────────────────────────────────────────────────────────
    def _meta(icon, value: str):
        return ft.Row(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=12, color=ft.Colors.GREY_400),
                ft.Text(value, size=11, color=ft.Colors.GREY_500,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True),
            ],
        )

    # ── enroll button ─────────────────────────────────────────────────────────
    view_btn = ft.ElevatedButton(
        content=ft.Text("View Course", size=13,
                        color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.W_600),
        bgcolor=ft.Colors.PRIMARY,
        expand=True,
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=0,
        ),
        on_click=on_view_click,
    )

    def handle_hover(e):
        e.control.scale = 1.05 if e.data == "true" else 1.0
        e.control.shadow = ft.BoxShadow(
            blur_radius=16 if e.data == "true" else 8,
            color=ft.Colors.with_opacity(0.12 if e.data == "true" else 0.08, ft.Colors.ON_SURFACE),
            offset=ft.Offset(0, 8) if e.data == "true" else ft.Offset(0, 3),
        )
        e.control.update()

    # ── card ──────────────────────────────────────────────────────────────────
    return ft.Container(
        # preserve original animation contract
        offset=ft.Offset(0, 0.1),
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        scale=1.0,
        animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
        on_hover=handle_hover,
        tooltip="Tap on this card to view course details",
        opacity=0,
        animate_opacity=300,
        bgcolor=ft.Colors.SURFACE,
        border_radius=ft.BorderRadius.only(top_left=32, bottom_right=32, top_right=8, bottom_left=8),
        shadow=ft.BoxShadow(
            blur_radius=8,
            color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
            offset=ft.Offset(0, 3),
        ),
        ink=True,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                # ── Cover ──────────────────────────────────────────────────
                cover,

                # ── Body ───────────────────────────────────────────────────
                ft.Container(
                    padding=ft.Padding.only(left=12, right=12, top=10, bottom=12),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            # Category + date on same row
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    category_pill,
                                    ft.Text(
                                        created_at or "",
                                        size=10,
                                        color=ft.Colors.GREY_400,
                                    ),
                                ],
                            ),

                            # Title
                            ft.Text(
                                course_title,
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),

                            # Author
                            _meta(ft.Icons.PERSON_OUTLINE_ROUNDED, course_author),

                            ft.Divider(height=1, color=ft.Colors.GREY_100),

                            # Enroll button
                            ft.Row(controls=[view_btn]),
                        ],
                    ),
                ),
            ],
        ),
    )