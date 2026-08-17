import asyncio
import flet as ft
import flet_charts as fch
from datetime import datetime
from src.components.bottom_appbar import get_bottom_appbar
from src.requests.enrollments import get_enrollment_stats


def format_time_ascension(seconds: int) -> str:
    if not seconds: return "—"
    try:
        seconds = int(seconds)
    except:
        return "—"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    w, d = divmod(d, 7)
    mo, w = divmod(w, 4)
    yr, mo = divmod(mo, 12)
    
    parts = []
    if yr > 0:
        parts.append(f"{yr}y")
        if mo > 0: parts.append(f"{mo}mo")
    elif mo > 0:
        parts.append(f"{mo}mo")
        if w > 0: parts.append(f"{w}w")
    elif w > 0:
        parts.append(f"{w}w")
        if d > 0: parts.append(f"{d}d")
    elif d > 0:
        parts.append(f"{d}d")
        if h > 0: parts.append(f"{h}h")
    elif h > 0:
        parts.append(f"{h}h")
        if m > 0: parts.append(f"{m}m")
    elif m > 0:
        parts.append(f"{m}m")
    else:
        parts.append(f"{s}s")
        
    return " ".join(parts)


async def course_stats_view(page: ft.Page, course_id: str) -> ft.View:

    # ── constants ────────────────────────────────────────────────────────────
    SURFACE       = ft.Colors.SURFACE
    ON_SURFACE    = ft.Colors.ON_SURFACE
    PRIMARY       = "#4F46E5" # Indigo 600
    PRIMARY_DARK  = "#312E81" # Indigo 900
    PRIMARY_LIGHT = "#E0E7FF" # Indigo 100
    GREY_100      = ft.Colors.GREY_100
    GREY_200      = ft.Colors.GREY_200
    GREY_400      = ft.Colors.GREY_400
    GREY_500      = ft.Colors.GREY_500
    GOLD          = "#F59E0B"
    GOLD_BG       = "#FFFBEB"
    GREEN         = "#10B981"
    GREEN_BG      = "#ECFDF5"
    BLUE          = "#3B82F6"
    BLUE_BG       = "#EFF6FF"
    PURPLE        = "#8B5CF6"
    PURPLE_BG     = "#F5F3FF"

    token = await page.shared_preferences.get("auth_token") or ""

    scroll_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)

    def _fmt_date(iso_str):
        if not iso_str: return "—"
        try:
            dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except:
            return str(iso_str)

    def _stat_card(icon, icon_color, bg_color, label, value, sub=None):
        card_ref = ft.Ref[ft.Container]()
        
        def on_hover(e):
            if e.data == "true":
                card_ref.current.scale = 1.02
                card_ref.current.shadow = ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK), offset=ft.Offset(0, 6))
            else:
                card_ref.current.scale = 1.0
                card_ref.current.shadow = ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2))
            card_ref.current.update()

        return ft.Container(
            ref=card_ref,
            bgcolor=SURFACE,
            border_radius=16,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.5, GREY_200)),
            padding=ft.Padding.all(16),
            scale=1.0,
            animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            on_hover=on_hover,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Container(
                        width=42, height=42,
                        border_radius=12,
                        bgcolor=bg_color,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, color=icon_color, size=22),
                    ),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(value, size=22, weight=ft.FontWeight.W_800, color=ON_SURFACE),
                            ft.Text(label, size=12, color=GREY_500, weight=ft.FontWeight.W_600),
                            *([ft.Text(sub, size=11, color=GREY_400)] if sub else []),
                        ],
                    ),
                ],
            ),
        )

    def _create_anim_container(content, margin=None):
        return ft.Container(
            content=content,
            opacity=0,
            margin=margin,
            offset=ft.Offset(0, 0.1),
            animate_opacity=ft.Animation(500, ft.AnimationCurve.DECELERATE),
            animate_offset=ft.Animation(500, ft.AnimationCurve.DECELERATE)
        )

    def build_content(s: dict):
        faster = s.get("faster_than_percentile", 0)
        rank   = s.get("leaderboard_rank")
        total  = s.get("total_completers", 0)
        cert   = s.get("certificate_download_url")
        auto_certificate = s.get("auto_certificate", True)

        anim_controls = []

        # ── Header ──
        header = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                colors=[PRIMARY, PRIMARY_DARK],
            ),
            border_radius=ft.BorderRadius.only(bottom_left=32, bottom_right=32),
            padding=ft.Padding.only(left=24, right=24, top=24, bottom=36),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row([
                        ft.Icon(ft.Icons.WORKSPACE_PREMIUM_ROUNDED, color=GOLD, size=24),
                        ft.Text("Course Completed", size=13, color=PRIMARY_LIGHT, weight=ft.FontWeight.W_700)
                    ], tight=True, spacing=6),
                    ft.Text(
                        s.get("course_title", "Course"),
                        size=26, weight=ft.FontWeight.W_900,
                        color=ft.Colors.WHITE,
                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Container(height=8),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Row(tight=True, spacing=6, controls=[
                                ft.Icon(ft.Icons.LOGIN_ROUNDED, size=14, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
                                ft.Text(f"Started: {_fmt_date(s.get('enrolled_at'))}", size=12, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                            ]),
                            ft.Row(tight=True, spacing=6, controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=14, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
                                ft.Text(f"Finished: {_fmt_date(s.get('completed_at'))}", size=12, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                            ]),
                        ],
                        wrap=True
                    ),
                ],
            ),
        )
        anim_controls.append(_create_anim_container(header))

        # ── Certificate ──
        if cert and auto_certificate:
            async def do_download(e):
                await page.launch_url(cert)
            cert_c = _create_anim_container(ft.Container(
                bgcolor=GOLD_BG,
                border_radius=16,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, GOLD)),
                padding=ft.Padding.all(20),
                margin=ft.Margin.only(bottom=16),
                shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.1, GOLD), offset=ft.Offset(0, 4)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=14, tight=True,
                            controls=[
                                ft.Container(
                                    width=46, height=46, border_radius=12,
                                    bgcolor=ft.Colors.with_opacity(0.15, GOLD),
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, color=GOLD, size=24),
                                ),
                                ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text("Certificate Ready!", size=15, weight=ft.FontWeight.W_800, color="#92400E"),
                                        ft.Text("Tap to download your verified certificate", size=10, color=ft.Colors.with_opacity(0.8, "#92400E")),
                                    ],
                                ),
                            ],
                        ),
                        ft.IconButton(
                            ft.Icons.DOWNLOAD_ROUNDED, icon_color=GOLD, icon_size=24,
                            tooltip="Download", on_click=lambda e: page.run_task(do_download, e),
                            style=ft.ButtonStyle(bgcolor=ft.Colors.WHITE)
                        ),
                    ],
                ),
            ))
            anim_controls.append(cert_c)

        # ── Stats Grid ──
        grid_c = _create_anim_container(
            ft.ResponsiveRow(
                columns=12, spacing=16, run_spacing=16,
                controls=[
                    ft.Container(col={"xs": 6}, content=_stat_card(ft.Icons.TIMER_OUTLINED, BLUE, BLUE_BG, "Time Spent", format_time_ascension(s.get("time_spent_seconds", 0)))),
                    ft.Container(col={"xs": 6}, content=_stat_card(ft.Icons.LEADERBOARD_ROUNDED, GOLD, GOLD_BG, "Rank", f"#{rank}" if rank else "—", f"of {total}" if total else None)),
                    ft.Container(col={"xs": 6}, content=_stat_card(ft.Icons.SPEED_ROUNDED, GREEN, GREEN_BG, "Faster Than", f"{faster}%", "of learners")),
                    ft.Container(col={"xs": 6}, content=_stat_card(ft.Icons.GROUP_ROUNDED, PURPLE, PURPLE_BG, "Completers", str(total) if total else "—")),
                ]
            ),
            margin=ft.Margin.only(bottom=24)
        )
        anim_controls.append(grid_c)

        # ── Speed Percentile Visuals (Chart + Ring) ──
        
        your_val = max(10, 100 - faster)
        avg_val = 50

        chart = fch.BarChart(
            groups=[
                fch.BarChartGroup(x=0, rods=[fch.BarChartRod(from_y=0, to_y=avg_val, width=28, color=GREY_400, border_radius=4, tooltip="Average Time")]),
                fch.BarChartGroup(x=1, rods=[fch.BarChartRod(from_y=0, to_y=your_val, width=28, color=GREEN, border_radius=4, tooltip="Your Time")]),
            ],
            bottom_axis=fch.ChartAxis(
                labels=[
                    fch.ChartAxisLabel(value=0, label=ft.Container(ft.Text("Avg", size=11, weight=ft.FontWeight.W_600, color=GREY_500), padding=5)),
                    fch.ChartAxisLabel(value=1, label=ft.Container(ft.Text("You", size=11, weight=ft.FontWeight.W_800, color=GREEN), padding=5)),
                ],
                label_size=32,
            ),
            left_axis=fch.ChartAxis(show_labels=False),
            tooltip=fch.BarChartTooltip(bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK)),
            interactive=True,
            expand=True,
            max_y=110,
        )

        speed_section = _create_anim_container(ft.Container(
            bgcolor=SURFACE,
            border_radius=16,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.5, GREY_200)),
            padding=ft.Padding.all(24),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            content=ft.Column(
                spacing=24,
                controls=[
                    ft.Text("Performance Comparison", size=16, weight=ft.FontWeight.W_800, color=ON_SURFACE),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                        spacing=24,
                        run_spacing=24,
                        controls=[
                            ft.Container(
                                width=120, height=120,
                                content=ft.Stack([
                                    ft.ProgressRing(value=1.0, color=GREY_100, stroke_width=8, width=100, height=100),
                                    ft.ProgressRing(value=faster/100, color=GREEN, stroke_width=8, width=100, height=100),
                                    ft.Container(
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Column(
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=0,
                                            controls=[
                                                ft.Text(f"Top", size=11, color=GREY_500, weight=ft.FontWeight.W_600),
                                                ft.Text(f"{100 - int(faster)}%", size=20, weight=ft.FontWeight.W_900, color=ON_SURFACE)
                                            ]
                                        )
                                    )
                                ])
                            ),
                            ft.Container(
                                width=140, height=140,
                                content=chart
                            )
                        ]
                    ),
                    ft.Text(f"You completed this course faster than {faster}% of all learners.", size=13, color=GREY_500, text_align=ft.TextAlign.CENTER)
                ]
            )
        ))
        anim_controls.append(speed_section)

        # Body padding wrapper
        body_col = ft.Column(
            spacing=0,
            controls=[
                anim_controls[0], # header
                ft.Container(
                    padding=ft.Padding.only(left=20, right=20, top=24, bottom=40),
                    content=ft.Column(spacing=0, controls=anim_controls[1:])
                )
            ]
        )

        return body_col, anim_controls

    async def fetch():
        try:
            stats = await get_enrollment_stats(token, course_id)
            body_col, anim_controls = build_content(stats)
            scroll_col.controls = [body_col]
            page.update()
            
            # Run staggered cascade
            for c in anim_controls:
                c.opacity = 1
                c.offset = ft.Offset(0, 0)
                page.update()
                await asyncio.sleep(0.08)

        except Exception as ex:
            scroll_col.controls = [
                ft.Container(
                    expand=True, alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=48, color=GREY_400),
                            ft.Text("Could not load stats", size=16, color=GREY_500, weight=ft.FontWeight.W_600),
                            ft.Text(str(ex), size=12, color=GREY_400),
                        ],
                    ),
                )
            ]
            page.update()

    scroll_col.controls = [ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=ft.ProgressRing(color=PRIMARY), padding=40)]
    page.run_task(fetch)

    return ft.View(
        route=f"/courses/{course_id}/stats",
        padding=0,
        bgcolor="#F8F9FA",
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color=ft.Colors.WHITE,
                icon_size=20,
                on_click=lambda _: page.go(f'/courses'),
            ),
            title=ft.Text("My Results", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
            bgcolor=PRIMARY,
            elevation=0,
            center_title=False,
        ),
        bottom_appbar=get_bottom_appbar(page),
        controls=[ft.SafeArea(expand=True, content=scroll_col)],
    )