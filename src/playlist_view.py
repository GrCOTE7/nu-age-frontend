import flet as ft
import asyncio
from src.requests.playlists import get_playlist
from src.requests.enrollments import enrol_user, get_enrollments

UI_ACCENT = ft.Colors.PRIMARY
def create_course_item(page: ft.Page, token, course_data, index, is_enrolled, on_refresh):
    c_id = course_data.get("id")
    c_name = course_data.get("name", "Untitled")

    card_ref = ft.Ref[ft.Container]()

    async def on_enroll_click(e):
        e.control.disabled = True
        e.control.text = "Enrolling..."
        page.update()
        await enrol_user(token, c_id, None)
        await on_refresh()

    def on_hover(e):
        if e.data == "true":
            card_ref.current.shadow = ft.BoxShadow(
                blur_radius=12, color=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY), offset=ft.Offset(0, 4)
            )
            card_ref.current.border = ft.Border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.PRIMARY))
        else:
            card_ref.current.shadow = None
            card_ref.current.border = ft.Border.all(1, ft.Colors.GREY_200)
        card_ref.current.update()

    if is_enrolled:
        btn = ft.ElevatedButton(
            "View Course",
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.ON_PRIMARY,
            style=ft.ButtonStyle(elevation=0, shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda e: page.go(f"/courses/{c_id}/view")
        )
    else:
        btn = ft.ElevatedButton(
            "Course Details",
            bgcolor=UI_ACCENT,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(elevation=0, shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda e, c_id=c_id: page.go(f"/courses/{c_id}")
        )

    return ft.Container(
        ref=card_ref,
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.Border.all(1, ft.Colors.GREY_200),
        on_hover=on_hover,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row([
                    ft.Container(
                        width=40, height=40,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=ft.Colors.with_opacity(0.1, UI_ACCENT),
                        border_radius=10,
                        content=ft.Text(f"{index}", size=16, weight=ft.FontWeight.BOLD, color=UI_ACCENT)
                    ),
                    ft.Text(c_name, size=16, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE),
                ], wrap=True, spacing=16),
                ft.Row([btn],alignment=ft.MainAxisAlignment.END)
            ]
        )
    )

async def playlist_view(page: ft.Page, playlist_id: str):
    token = None

    playlist_data = {}
    playlist_courses = []
    user_enrollments = []

    main_socket = ft.Ref[ft.Container]()

    async def load_data():
        nonlocal playlist_data, playlist_courses, user_enrollments, token
        token = await page.shared_preferences.get("auth_token")
        playlist_data = await get_playlist(token, playlist_id)
        if "error" not in playlist_data:
            raw_courses = playlist_data.get("playlist_courses", [])
            playlist_courses = [item.get("course", {}) for item in raw_courses if "course" in item]

        user_enrollments = await get_enrollments(token, None)
        if not isinstance(user_enrollments, list):
            user_enrollments = []

    async def refresh_view():
        await load_data()
        main_socket.current.alignment = None
        main_socket.current.content = build_view()
        page.update()

    async def on_bulk_enroll(e):
        e.control.disabled = True
        e.control.content = ft.Row([ft.ProgressRing(width=16, height=16, color=ft.Colors.PRIMARY, stroke_width=2), ft.Text("Enrolling....")])
        page.update()

        enrolled_course_ids = [c.get("id") for c in user_enrollments]

        for c in playlist_courses:
            c_id = c.get("id")
            if c_id not in enrolled_course_ids:
                await enrol_user(token, c_id, None)

        await refresh_view()

    def build_view():
        if not playlist_data or "error" in playlist_data:
            return ft.Container(
                content=ft.Text("Error loading playlist or playlist not found", color=ft.Colors.RED),
                padding=40,
                alignment=ft.Alignment.CENTER
            )

        is_mobile = page.width is not None and page.width < 600

        title = playlist_data.get("name", "Untitled Playlist")
        desc = playlist_data.get("description", "No description provided.")
        image_url = playlist_data.get("image_url", None)

        enrolled_course_ids = [e.get("id") for e in user_enrollments]
        all_enrolled = all(c.get("id") in enrolled_course_ids for c in playlist_courses) if playlist_courses else True

        course_controls = []
        for idx, c in enumerate(playlist_courses):
            is_enrolled = c.get("id") in enrolled_course_ids
            course_controls.append(create_course_item(page, token, c, idx + 1, is_enrolled, refresh_view))

        if not course_controls:
            course_controls.append(ft.Container(
                padding=40,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("This playlist has no courses yet.", color=ft.Colors.GREY_500, size=16)
            ))

        header_content = ft.Column(
            spacing=10 if is_mobile else 16,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                    border_radius=20,
                    content=ft.Text(
                        "LEARNING PATH", size=9 if is_mobile else 10,
                        weight=ft.FontWeight.W_800, color=ft.Colors.WHITE
                    )
                ),
                ft.Text(
                    title, size=22 if is_mobile else 33,
                    weight=ft.FontWeight.W_900, color=ft.Colors.WHITE,
                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS
                ),
                ft.Text(
                    desc, size=13 if is_mobile else 16, color=ft.Colors.WHITE70,
                    max_lines=2 if is_mobile else 3, overflow=ft.TextOverflow.ELLIPSIS
                ),
                ft.Container(height=4 if is_mobile else 8),
            ]
        )

        if not all_enrolled and playlist_courses:
            header_content.controls.append(
                ft.ElevatedButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=UI_ACCENT, size=18 if is_mobile else 20),
                         ft.Text("Bulk Enroll in Playlist", weight=ft.FontWeight.BOLD, size=13 if is_mobile else 14)],
                        tight=True, spacing=8, alignment=ft.MainAxisAlignment.CENTER
                    ),
                    bgcolor=ft.Colors.WHITE,
                    color=UI_ACCENT,
                    height=44 if is_mobile else 48,
                    width=float("inf") if is_mobile else None,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=4),
                    on_click=on_bulk_enroll
                )
            )
        elif all_enrolled and playlist_courses:
            header_content.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12 if is_mobile else 16, vertical=10 if is_mobile else 12),
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                    border_radius=12,
                    content=ft.Row(
                        [ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ft.Colors.WHITE, size=16),
                         ft.Text("You are enrolled in all courses", color=ft.Colors.WHITE,
                                 weight=ft.FontWeight.BOLD, size=12 if is_mobile else 14)],
                        wrap=True, spacing=8
                    )
                )
            )

        if image_url:
            header = ft.Container(
                height=220 if is_mobile else 350,
                border_radius=16 if is_mobile else 24,
                image=ft.DecorationImage(
                    src=image_url,
                    fit=ft.BoxFit.COVER,
                ),
                content=ft.Container(
                    padding=ft.Padding.all(18 if is_mobile else 40),
                    alignment=ft.Alignment.BOTTOM_LEFT,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_CENTER,
                        end=ft.Alignment.BOTTOM_CENTER,
                        colors=[ft.Colors.TRANSPARENT, ft.Colors.BLACK87]
                    ),
                    content=header_content
                )
            )
        else:
            header = ft.Container(
                padding=ft.Padding.all(6 if is_mobile else 10),
                border_radius=16 if is_mobile else 24,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[UI_ACCENT, ft.Colors.SECONDARY]
                ),
                content=ft.Container(
                    padding=ft.Padding.all(16 if is_mobile else 0),
                    content=header_content
                )
            )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=30,
            expand=True,
            controls=[
                ft.Container(
                    margin=ft.Margin.only(bottom=-10),
                    content=ft.IconButton(
                        ft.Icons.ARROW_BACK_ROUNDED,
                        on_click=lambda _: page.go("/courses"),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST)
                    )
                ),
                header,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=10),
                    content=ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text("Courses in this Playlist", size=22, weight=ft.FontWeight.W_800, color=ft.Colors.ON_SURFACE),
                            ft.Column(controls=[*course_controls])
                        ]
                    )
                ),
                ft.Container(height=40)  # Bottom padding
            ]
        )

    content = ft.Container(
        ref=main_socket,
        expand=True,
        alignment=ft.Alignment(0, 0),
        padding=ft.Padding.symmetric(
            horizontal=16 if page.width and page.width < 600 else 32,
            vertical=20
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.ProgressRing(color=UI_ACCENT), ft.Text("Loading Playlist Details...")]
        )
    )

    asyncio.create_task(refresh_view())
    return ft.View(
        route=f"/playlists/{playlist_id}",
        controls=[ft.SafeArea(expand=True, content=content)]
    )