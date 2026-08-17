import flet as ft
import urllib.parse
import asyncio
from src.components.bottom_appbar import get_bottom_appbar
from src.requests.auth import logout_request
from src.requests.enrollments import get_enrollments

async def profile_view(page: ft.Page):

    # ── Palette ───────────────────────────────────────────────────────────────
    PAGE_BG       = ft.Colors.ON_PRIMARY
    CARD_BG       = ft.Colors.SURFACE
    LABEL_COLOR   = ft.Colors.ON_SURFACE_VARIANT
    VALUE_COLOR   = ft.Colors.ON_SURFACE
    DIVIDER_CLR   = ft.Colors.OUTLINE_VARIANT
    ICON_BG       = ft.Colors.with_opacity(0.08, ft.Colors.PRIMARY)

    # ── Initial Loading Socket ────────────────────────────────────────────────
    content_socket = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(color=ft.Colors.PRIMARY, stroke_width=3)
    )

    async def execute_logout(e):
        refresh_token = await page.shared_preferences.get("refresh_token")
        if refresh_token:
            try:
                await logout_request(refresh_token)
            except Exception:
                pass
        await page.shared_preferences.remove("refresh_token")
        await page.shared_preferences.remove("auth_token")
        page.go("/")
        page.update()

    logout_confirmation_dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=16),
        title=ft.Row([
            ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=ft.Colors.RED_400, size=20),
            ft.Text("Log out?", weight=ft.FontWeight.BOLD, size=16)
        ], spacing=10),
        content=ft.Text(
            "You'll need to sign back in to access your courses and progress.",
            size=13,
            color=ft.Colors.ON_SURFACE_VARIANT
        ),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT), on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Log out", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400, color=ft.Colors.ON_PRIMARY, shape=ft.RoundedRectangleBorder(radius=8)), on_click=execute_logout)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        actions_padding=ft.Padding(left=16, right=16, top=0, bottom=16)
    )

    async def handle_logout(e):
        if logout_confirmation_dialog.open: return
        e.control.disabled = True
        e.control.update()
        try:
            page.show_dialog(logout_confirmation_dialog)
            page.update()
        finally:
            e.control.disabled = False
            try: e.control.update()
            except Exception: pass

    async def load_profile():
        user_data  = page.session.store.get("current_user")
        first_name = user_data.get("first_name", "")
        last_name  = user_data.get("last_name", "")
        full_name  = f"{first_name} {last_name}".strip()
        email      = user_data.get("email", "—")
        username   = user_data.get("username", "—")
        gender     = user_data.get("gender", "—")
        role       = user_data.get("role", "—")
        university = user_data.get("university")
        streak = user_data.get("streak", 0)

        initials = "".join([n[0] for n in full_name.split()[:2]]).upper() if full_name else "?"

        token = await page.shared_preferences.get("auth_token")

        try:
            enrolled_list = await asyncio.wait_for(get_enrollments(token, None), timeout=15)
            if not isinstance(enrolled_list, list):
                enrolled_list = []
        except (asyncio.TimeoutError, Exception):
            enrolled_list = []
            
        active_count = len(enrolled_list)
        finished_count = sum(1 for c in enrolled_list if c.get("progress", 0.0) >= 100)

        # ── Hero header ───────────────────────────────────────────────────────
        header = ft.Container(
            bgcolor=ft.Colors.PRIMARY,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ft.Colors.PRIMARY, ft.Colors.SECONDARY]
            ),
            padding=ft.Padding(top=50, bottom=36, left=20, right=20),
            border_radius=ft.BorderRadius(bottom_left=28, bottom_right=28, top_left=0, top_right=0),
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY), offset=ft.Offset(0, 6)),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                controls=[
                    ft.Container(
                        width=86, height=86, border_radius=43, bgcolor=ft.Colors.ON_PRIMARY, alignment=ft.Alignment.CENTER,
                        shadow=ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK), offset=ft.Offset(0, 4)),
                        content=ft.Container(
                            width=78, height=78, border_radius=39, bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.ON_PRIMARY),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(initials, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
                        )
                    ),
                    ft.Container(height=2),
                    ft.Text(full_name, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=14, vertical=5),
                        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.ON_PRIMARY),
                        border_radius=20, border=ft.Border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.ON_PRIMARY)),
                        content=ft.Text(role.title(), size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_PRIMARY)
                    )
                ]
            )
        )

        header_stack = ft.Stack([
            header,
            ft.Container(content=ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED, icon_color=ft.Colors.ON_PRIMARY, icon_size=20, tooltip="Log out", on_click=handle_logout, style=ft.ButtonStyle(bgcolor={"": ft.Colors.with_opacity(0.18, ft.Colors.ON_PRIMARY)}, shape=ft.CircleBorder())), top=12, left=12),
            ft.Container(content=ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=ft.Colors.ON_PRIMARY, icon_size=20, tooltip="Edit profile", on_click=lambda _: page.go("/edit-profile"), style=ft.ButtonStyle(bgcolor={"": ft.Colors.with_opacity(0.18, ft.Colors.ON_PRIMARY)}, shape=ft.CircleBorder())), top=12, right=12)
        ])

        # ── Share CTA (Top) ───────────────────────────────────────────────────
        async def open_whatsapp(e):
            message = """Just found Nu Age and it's honestly a game changer for studying! It has highly paid courses, an AI tutor and quality tutors!

Check it out 👉 : nu-age.name.ng

Pro tip: share it with a friend and you unlock extra study hub generations, it's worth it!"""
            encoded_message = urllib.parse.quote(message)
            await page.launch_url(f"https://wa.me/?text={encoded_message}")

        def handle_share_hover(e):
            e.control.scale = 1.02 if e.data == "true" else 1.0
            e.control.update()

        share_cta = ft.Container(
            ink=True,
            on_click=open_whatsapp,
            on_hover=handle_share_hover,
            scale=1.0,
            animate_scale=ft.Animation(200, ft.AnimationCurve.DECELERATE),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.REDEEM_ROUNDED, color=ft.Colors.WHITE, size=28),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text("Refer & Earn Rewards", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text("Share Nu-Age to unlock extra study features!", size=11, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE))
                        ]
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=ft.Colors.WHITE)
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                colors=[ft.Colors.AMBER_500, ft.Colors.ORANGE_600]
            ),
            border_radius=16,
            shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.2, ft.Colors.ORANGE_600), offset=ft.Offset(0, 4)),
        )

        # ── Learning Stats (Grid) ─────────────────────────────────────────────
        def handle_stat_hover(e):
            e.control.scale = 1.05 if e.data == "true" else 1.0
            e.control.shadow = ft.BoxShadow(
                blur_radius=16 if e.data == "true" else 6,
                color=ft.Colors.with_opacity(0.12 if e.data == "true" else 0.05, ft.Colors.BLACK),
                offset=ft.Offset(0, 6) if e.data == "true" else ft.Offset(0, 2),
            )
            e.control.update()

        def stat_card(icon, color, value, label, delay):
            return ft.Container(
                expand=True,
                bgcolor=CARD_BG,
                border_radius=16,
                padding=ft.Padding.all(16),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.BLACK)),
                shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
                ink=True,
                scale=1.0,
                animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
                on_hover=handle_stat_hover,
                opacity=0,
                offset=ft.Offset(0, 0.2),
                animate_opacity=ft.Animation(400, ft.AnimationCurve.DECELERATE),
                animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
                data=delay, # Store delay for the animation loop
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=40, height=40, border_radius=20,
                            bgcolor=ft.Colors.with_opacity(0.1, color),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, color=color, size=20)
                        ),
                        ft.Column(
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=VALUE_COLOR),
                                ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=LABEL_COLOR, text_align=ft.TextAlign.CENTER)
                            ]
                        )
                    ]
                )
            )

        streak_card = stat_card(ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, ft.Colors.ORANGE_500, streak, "Day Streak", 0.0)
        active_card = stat_card(ft.Icons.LIBRARY_BOOKS_ROUNDED, ft.Colors.INDIGO_500, active_count, "Enrolled", 0.1)
        completed_card = stat_card(ft.Icons.EMOJI_EVENTS_ROUNDED, ft.Colors.GREEN_500, finished_count, "Completed", 0.2)
        
        stats_row = ft.Row(
            spacing=12,
            controls=[streak_card, active_card, completed_card]
        )

        # ── Account Details ───────────────────────────────────────────────────
        def info_row(icon, label, value, is_last=False):
            return ft.Column([
                ft.Container(
                    padding=ft.Padding(left=16, right=16, top=14, bottom=14),
                    content=ft.Row([
                        ft.Container(width=38, height=38, border_radius=10, bgcolor=ICON_BG, alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color=ft.Colors.PRIMARY, size=18)),
                        ft.Container(width=14),
                        ft.Column([
                            ft.Text(label, size=11, color=LABEL_COLOR, weight=ft.FontWeight.W_500),
                            ft.Text(str(value).title() if label not in ("Email", "Username") else str(value), size=14, weight=ft.FontWeight.W_600, color=VALUE_COLOR)
                        ], spacing=2, tight=True, expand=True)
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
                ),
                ft.Container() if is_last else ft.Container(content=ft.Divider(height=1, color=DIVIDER_CLR), padding=ft.Padding(left=68, right=0, top=0, bottom=0))
            ], spacing=0, tight=True)

        rows_data = [
            (ft.Icons.ALTERNATE_EMAIL_ROUNDED, "Email", email),
            (ft.Icons.BADGE_OUTLINED, "Username", username),
            (ft.Icons.MALE if str(gender).lower() == "male" else ft.Icons.FEMALE, "Gender", gender)
        ]
        if university:
            rows_data.append((ft.Icons.ACCOUNT_BALANCE_ROUNDED, "University", university))

        row_controls = []
        for index, row_info in enumerate(rows_data):
            row_controls.append(info_row(row_info[0], row_info[1], row_info[2], index == len(rows_data) - 1))

        info_card = ft.Container(
            bgcolor=CARD_BG, border_radius=16, border=ft.Border.all(1, ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
            shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Column(row_controls, spacing=0, tight=True)
        )

        # ── Quick-action strip ────────────────────────────────────────────────
        def quick_action(icon, label, on_click=None):
            return ft.Container(
                expand=True, bgcolor=CARD_BG, border_radius=12, border=ft.Border.all(1, ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
                shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
                ink=True, on_click=on_click, padding=ft.Padding(left=12, right=12, top=14, bottom=14),
                content=ft.Column([
                    ft.Container(width=36, height=36, border_radius=10, bgcolor=ICON_BG, alignment=ft.Alignment.CENTER, content=ft.Icon(icon, color=ft.Colors.PRIMARY, size=18)),
                    ft.Container(height=8),
                    ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=VALUE_COLOR, text_align=ft.TextAlign.CENTER, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True)
            )

        actions_row = ft.Row([
            quick_action(ft.Icons.MENU_BOOK_ROUNDED, "My Courses", lambda _: page.go("/courses")),
            quick_action(ft.Icons.SETTINGS_OUTLINED, "Settings", lambda _: page.go("/edit-profile")),
        ], spacing=12)

        async def on_toggle(e):
            await page.data["toggle_dark_mode"]()

        dark_switch = ft.IconButton(icon=ft.Icons.DARK_MODE, tooltip="Toggle dark mode", on_click=on_toggle)

        def section_label(text):
            return ft.Text(text.upper(), size=11, weight=ft.FontWeight.W_700, color=LABEL_COLOR)

        body = ft.Container(
            padding=ft.Padding(left=20, right=20, top=24, bottom=24),
            content=ft.Column(
                spacing=24,
                controls=[
                    share_cta,
                    ft.Column(spacing=12, controls=[section_label("Learning Stats"), stats_row]),
                    ft.Row(controls=[ft.Text("TOGGLE APPEARANCE: ", size=11, weight=ft.FontWeight.W_700, color=LABEL_COLOR), dark_switch]),
                    ft.Column(spacing=12, controls=[section_label("Quick Actions"), actions_row]),
                    ft.Column(spacing=12, controls=[section_label("Account Details"), info_card]),
                ]
            )
        )

        content_socket.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[header_stack, body]
        )
        page.update()

        # Trigger animations for stat cards stagger-style
        for stat in [streak_card, active_card, completed_card]:
            await asyncio.sleep(stat.data) # delay
            stat.opacity = 1
            stat.offset = ft.Offset(0, 0)
            page.update()

    page.run_task(load_profile)

    return ft.View(
        route="/profile",
        bgcolor=PAGE_BG,
        padding=0,
        bottom_appbar=get_bottom_appbar(page),
        controls=[
            ft.SafeArea(
                expand=True,
                content=content_socket
            )
        ]
    )