import asyncio

import flet as ft
from src.requests.Courses import get_courses
from src.requests.enrollments import get_enrollments, enrol_user


# ─────────────────────────────────────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────────────────────────────────────
async def course_details_view(page: ft.Page, course_id: str, back_target: str = "/courses"):
    # ── content socket ────────────────────────────────────────────────────────
    content_socket = ft.Container(
        expand=True,
        padding=ft.Padding.only(top=24),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.ProgressRing(color=ft.Colors.PRIMARY, width=36, height=36),
                ft.Text("Loading course details…", size=13, color=ft.Colors.GREY_500),
            ],
        ),
    )

    # ── app bar ───────────────────────────────────────────────────────────────
    app_bar = ft.AppBar(
        bgcolor=ft.Colors.SURFACE,
        title=ft.Text(
            "Course Details",
            color=ft.Colors.ON_SURFACE,
            weight=ft.FontWeight.W_700,
            size=17,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
        leading=ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color=ft.Colors.ON_SURFACE,
            on_click=lambda _: page.go(back_target), 
        ),
        elevation=0,
    )

    # ── enrol handler (defined early so load_course_info can close over it) ──
    async def handle_enrol_click(e, is_enrolling: bool):
        if e.control.disabled:
            return

        token = await page.shared_preferences.get("auth_token")
        e.control.disabled = True
        e.control.content = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
            spacing=6,
            controls=[
                ft.ProgressRing(width=14, height=14,
                                color=ft.Colors.ON_PRIMARY, stroke_width=2),
                ft.Text("Please wait…", color=ft.Colors.ON_PRIMARY,
                        size=13, weight=ft.FontWeight.W_600),
            ],
        )
        page.update()

        try:
            status, data = await asyncio.wait_for(
                enrol_user(token, course_id, None), timeout=15
            )
            if status == 200:
                 page.go(f"/courses/{course_id}/view")
            else:
                e.control.disabled = False
                e.control.content = ft.Text(
                    "Unenroll" if is_enrolling else "Enroll Now",
                    color=ft.Colors.ON_PRIMARY,
                    size=14,
                    weight=ft.FontWeight.W_600,
                )
                page.update()

        except asyncio.TimeoutError:
            e.control.disabled = False
            e.control.content = ft.Text(
                "Timed out — tap to retry",
                color=ft.Colors.ON_PRIMARY, size=13,
            )
            page.update()

        except Exception:
            e.control.disabled = False
            e.control.content = ft.Text(
                "Error — tap to retry",
                color=ft.Colors.ON_PRIMARY, size=13,
            )
            page.update()

    # ─────────────────────────────────────────────────────────────────────────
    # DATA LOADER
    # ─────────────────────────────────────────────────────────────────────────
    async def load_course_info(cid: str):
        token = await page.shared_preferences.get("auth_token")

        try:
            course_list, enrolled_list = await asyncio.gather(
                asyncio.wait_for(get_courses(token, params={"id": cid}), timeout=15),
                asyncio.wait_for(get_enrollments(token, None),           timeout=15),
                return_exceptions=True,
            )

            # ── handle individual failures ─────────────────────────────────
            if isinstance(course_list, Exception) or not course_list:
                _show_error("Course not found or failed to load.")
                return

            if isinstance(enrolled_list, Exception):
                enrolled_list = []  # non-fatal — degrade gracefully

            # ── parse data ────────────────────────────────────────────────
            course_data = course_list[0]
            name        = course_data.get("name", "Untitled Course")
            image_url   = course_data.get("image_url")
            description = course_data.get("description", "No description provided.")
            objectives  = course_data.get("objectives", [])
            category    = (course_data.get("category") or {}).get("name", "Uncategorised")
            admin       = course_data.get("admin") or {}
            author      = f'{admin.get("first_name","Unknown")} {admin.get("last_name","Instructor")}'.strip()
            enrolled_count = len(course_data.get("Students", []))
            is_public_val = str(course_data.get("public", "false")).lower()
            is_supervised = course_data.get("supervised", False)
            rating = round(course_data.get("rating", 3.5),1)
            print(rating)

            enrolled_ids       = [c.get("id") for c in (enrolled_list or [])]
            is_already_enrolled = cid in enrolled_ids

            # ── update appbar title ───────────────────────────────────────
            view.appbar.title = ft.Text(
                name, color=ft.Colors.ON_SURFACE,
                weight=ft.FontWeight.W_700, size=17,
                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
            )

            # ── helpers ───────────────────────────────────────────────────
            def pill(label, bg, fg):
                return ft.Container(
                    padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                    bgcolor=bg, border_radius=10,
                    content=ft.Text(label, size=10, color=fg,
                                    weight=ft.FontWeight.W_600),
                )

            def section_label(text: str) -> ft.Text:
                return ft.Text(text, size=11, weight=ft.FontWeight.W_600,
                               color=ft.Colors.GREY_500)

            def info_row(icon, label, value):
                return ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=34, height=34,
                            border_radius=8,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, size=16,
                                            color=ft.Colors.PRIMARY),
                        ),
                        ft.Column(
                            spacing=1,
                            controls=[
                                ft.Text(label, size=10, color=ft.Colors.GREY_400,
                                        weight=ft.FontWeight.W_500),
                                ft.Text(value, size=13, color=ft.Colors.ON_SURFACE,
                                        weight=ft.FontWeight.W_600),
                            ],
                        ),
                    ],
                )

            def bullet_item(text: str):
                return ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            width=6, height=6,
                            margin=ft.Margin.only(top=6),
                            bgcolor=ft.Colors.PRIMARY,
                            border_radius=3,
                        ),
                        ft.Text(text, size=13, color=ft.Colors.ON_SURFACE,
                                expand=True),
                    ],
                )

            # ── status badges ─────────────────────────────────────────────
            badges = ft.Row(
                spacing=8,
                controls=[
                    pill("Public", ft.Colors.GREEN_50, ft.Colors.GREEN_700) if is_public_val == "true" else (
                        pill("Organization", ft.Colors.BLUE_50, ft.Colors.BLUE_700) if is_public_val == "organisation" else
                        pill("Draft", ft.Colors.GREY_100, ft.Colors.GREY_600)
                    ),
                    pill(
                        "Instructor-Led" if is_supervised else "Self-Paced",
                        ft.Colors.BLUE_50 if is_supervised else ft.Colors.PURPLE_50,
                        ft.Colors.BLUE_700 if is_supervised else ft.Colors.PURPLE_700,
                    ),
                ],
            )

            # ── objectives ────────────────────────────────────────────────
            obj_controls = (
                [bullet_item(o) for o in objectives]
                if objectives
                else [bullet_item(f"Gain knowledge in {name}")]
            )

            # ── enrol button ──────────────────────────────────────────────
            enrol_btn = ft.ElevatedButton(
                content=ft.Text(
                    "Unenroll" if is_already_enrolled else "Get Enrolled now " if not is_already_enrolled else "Enroll Now",
                    color=ft.Colors.ON_PRIMARY,
                    size=14,
                    weight=ft.FontWeight.W_600,
                ),
                bgcolor=(
                    ft.Colors.RED_600
                    if is_already_enrolled
                    else ft.Colors.ORANGE_700 # Matched from design
                ),
                height=48,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=24),
                    elevation=0,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=0)
                ),
                on_click=lambda e: page.run_task(
                    handle_enrol_click, e, is_already_enrolled
                ),
            )

            # ── card wrapper ──────────────────────────────────────────────
            def card(content):
                return ft.Container(
                    width=float("inf"),
                    bgcolor=ft.Colors.SURFACE,
                    border_radius=14,
                    border=ft.Border.all(1, ft.Colors.GREY_200),
                    padding=ft.Padding.symmetric(horizontal=18, vertical=16),
                    shadow=ft.BoxShadow(
                        blur_radius=6,
                        color=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                        offset=ft.Offset(0, 2),
                    ),
                    content=content,
                )

            # ── 1. Hero Banner ─────────────────────────────────────────────
            def build_star_row(rating: float, max_stars: int = 5):
                full = int(rating)
                frac = rating - full
                half = 1 if frac > 0.5 else 0
                empty = max_stars - full - half

                stars = (
                    [ft.Icon(ft.Icons.STAR_ROUNDED, color=ft.Colors.AMBER_400, size=20) for _ in range(full)]
                    + ([ft.Icon(ft.Icons.STAR_HALF_ROUNDED, color=ft.Colors.AMBER_400, size=20)] if half else [])
                    + [ft.Icon(ft.Icons.STAR_BORDER_ROUNDED, color=ft.Colors.AMBER_400, size=20) for _ in range(empty)]
                )

                return ft.Row(
                    spacing=4,
                    controls=stars + [ft.Text(f"({rating})", color=ft.Colors.WHITE70, size=14, weight=ft.FontWeight.W_600)]
    )
            hero_left = ft.Column(
                expand=True,
                spacing=24,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    badges,
                    ft.Text(
                        name,
                        size=30,
                        weight=ft.FontWeight.W_800,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Text(
                        description,
                        size=15,
                        color=ft.Colors.WHITE70,
                        max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Row(
                        spacing=24,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                        controls=[
                            enrol_btn,
                                build_star_row(rating)
                        ]
                    )
                ]
            )

            hero_right = ft.Container(
                border_radius=16,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK), offset=ft.Offset(0, 12)),
                content=ft.Image(
                    src=image_url if image_url else "assets/placeholder.png",
                    fit=ft.BoxFit.COVER,
                    width=float("inf"),
                    height=250,
                )
            )

            hero_section = ft.Container(
                bgcolor=ft.Colors.PRIMARY, # Deep premium navy background matching the design
                padding=ft.Padding.symmetric(horizontal=48, vertical=64),
                border_radius=25,
                content=ft.ResponsiveRow(
                    columns=12,
                    spacing=48,
                    run_spacing=48,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(content=hero_left, col={"xs": 12, "md": 7}),
                        ft.Container(content=hero_right, col={"xs": 12, "md": 5})
                    ]
                )
            )

            # ── 2. Bottom Content ──────────────────────────────────────────
            modules = course_data.get("modules", [])
            module_previews = []
            if modules:
                for idx, mod in enumerate(modules, 1):
                    mod_title = mod.get("title", f"Module {idx}")
                    module_previews.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(vertical=16, horizontal=20),
                            border_radius=12,
                            border=ft.Border.all(1, ft.Colors.GREY_200),
                            bgcolor=ft.Colors.SURFACE,
                            content=ft.Row(
                                spacing=16,
                                controls=[
                                    ft.Container(
                                        width=32, height=32,
                                        alignment=ft.Alignment.CENTER,
                                        bgcolor=ft.Colors.BLUE_50,
                                        border_radius=16,
                                        content=ft.Text(str(idx), size=14, color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_700)
                                    ),
                                    ft.Text(mod_title, size=15, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE, expand=True),
                                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, color=ft.Colors.GREY_400)
                                ]
                            )
                        )
                    )
            else:
                module_previews.append(
                    ft.Container(
                        padding=ft.Padding.all(24),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("No modules available for preview.", color=ft.Colors.GREY_500, size=14)
                    )
                )

            main_content = ft.Column(
                spacing=48,
                controls=[
                    # Overview
                    ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text("Course Overview", size=24, weight=ft.FontWeight.W_800, color=ft.Colors.ON_SURFACE),
                            ft.Text(description, size=15, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True, weight=ft.FontWeight.W_400)
                        ]
                    ),
                    # Objectives
                    ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text("What you will learn", size=24, weight=ft.FontWeight.W_800, color=ft.Colors.ON_SURFACE),
                            ft.Column(spacing=12, controls=obj_controls)
                        ]
                    )
                ]
            )

            org_name = (course_data.get("organisation") or {}).get("name", "Independent")
            
            sidebar_content = ft.Column(
                spacing=32,
                controls=[
                    # Modules Outline
                    ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text("Course Modules", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.ON_SURFACE),
                            ft.Column(spacing=12, controls=module_previews)
                        ]
                    ),
                    # Meta Info
                    card(
                        ft.Column(
                            spacing=16,
                            controls=[
                                ft.Text("Course Details", size=16, weight=ft.FontWeight.W_700),
                                info_row(ft.Icons.PERSON_OUTLINE_ROUNDED, "Instructor", author),
                                info_row(ft.Icons.BUSINESS_ROUNDED, "Organisation", org_name),
                                info_row(ft.Icons.CATEGORY_OUTLINED, "Category", category)
                            ]
                        )
                    )
                ]
            )

            bottom_section = ft.Container(
                padding=ft.Padding.symmetric(horizontal=48, vertical=48),
                content=ft.ResponsiveRow(
                    columns=12,
                    spacing=48,
                    run_spacing=48,
                    controls=[
                        ft.Container(content=main_content, col={"xs": 12, "md": 7}),
                        ft.Container(content=sidebar_content, col={"xs": 12, "md": 5})
                    ]
                )
            )

            real_content = ft.Column(
                spacing=0,
                controls=[
                    hero_section,
                    bottom_section
                ]
            )

            content_socket.alignment = None
            content_socket.padding   = 0
            content_socket.content   = real_content
            page.update()

        except asyncio.TimeoutError:
            _show_error(
                "Connection timed out.",
                icon=ft.Icons.WIFI_OFF_ROUNDED,
                color=ft.Colors.ORANGE_400,
            )

        except Exception as ex:
            _show_error(
                f"Something went wrong ({type(ex).__name__}).",
                icon=ft.Icons.ERROR_OUTLINE_ROUNDED,
                color=ft.Colors.RED_400,
            )

    # ── error helper ──────────────────────────────────────────────────────────
    def _show_error(message: str,
                    icon=ft.Icons.ERROR_OUTLINE_ROUNDED,
                    color=ft.Colors.RED_400):
        content_socket.alignment = ft.Alignment.CENTER
        content_socket.content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Icon(icon, size=48, color=color),
                ft.Text("Couldn't load course", size=16,
                        weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE),
                ft.Text(message, size=13, color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=4),
                ft.ElevatedButton(
                    "Retry",
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.ON_PRIMARY,
                    height=42,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        elevation=0,
                    ),
                    on_click=lambda _: page.run_task(load_course_info, course_id),
                ),
            ],
        )
        page.update()

    # ── trigger ───────────────────────────────────────────────────────────────
    page.run_task(load_course_info, course_id)

    # ── view ──────────────────────────────────────────────────────────────────
    view = ft.View(
        route=f"/courses/{course_id}",
        padding=0,
        bgcolor=ft.Colors.SURFACE,
        appbar=app_bar,
        scroll=ft.ScrollMode.AUTO,
        controls=[content_socket],
    )
    return view