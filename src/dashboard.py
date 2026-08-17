import asyncio
import sqlite3
from datetime import datetime, timedelta

import flet as ft
import flet_charts as fch  # pyright: ignore[reportMissingImports]

from src.components import bottom_appbar
from src.components.bottom_appbar import get_bottom_appbar
from src.components.dashboard_card import get_continue_learning_card
from src.requests.enrollments import get_enrollments
from src.utils.db_manager import get_weekly_activity
from src.requests.chats import get_all_users
from src.utils.quotes import get_random_quote, get_random_greeting, get_random_tip

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _section_label(text: str) -> ft.Text:
    return ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_500)


def _card(content, padding=18) -> ft.Container:
    return ft.Container(
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.Border.all(1, ft.Colors.GREY_200),
        padding=padding,
        shadow=ft.BoxShadow(
            blur_radius=8,
            color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
            offset=ft.Offset(0, 3),
        ),
        content=content,
        opacity=0,
        offset=ft.Offset(0, 0.2),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ONBOARDING — first-login welcome carousel
# ─────────────────────────────────────────────────────────────────────────────

# Edit this list to change the slides — nothing else needs to change.
# Set a slide's "image" to a real screenshot/illustration path or URL to
# replace the icon placeholder; leave it unset to keep the icon.
ONBOARDING_SLIDES = [
    {
        "eyebrow": "Your library",
        "accent": ft.Colors.PRIMARY,
        "icon_bg": ft.Colors.INDIGO_100,
        "icon": ft.Icons.LIBRARY_BOOKS_ROUNDED,
        "image": "coureses.png",  # e.g. "/assets/onboarding/courses.png"
        "title": "Everything you're learning,\nin one place",
        "body": "Jump back into any course, track chapters you've finished, "
                "and pick up exactly where you left off.",
    },
    {
        "eyebrow": "Study together",
        "accent": ft.Colors.TEAL_600,
        "icon_bg": ft.Colors.TEAL_100,
        "icon": ft.Icons.PEOPLE_ALT_ROUNDED,
        "image": "nu chat 3.png",  # e.g. "/assets/onboarding/network.png"
        "title": "Learn alongside people,\nnot alone",
        "body": "Add classmates, see what they're studying, and keep each "
                "other moving forward.",
    },
    {
        "eyebrow": "AI - Working for You",
        "accent": ft.Colors.AMBER_700,
        "icon_bg": ft.Colors.AMBER_100,
        "icon": ft.Icons.BAR_CHART_ROUNDED,
        "image": "cards.png",  # e.g. "/assets/onboarding/activity.png"
        "title": "Learn\nBut Smarter",
        "body": "Learn. Test. Repeat. Engage your own AI Tutor in the Self-Study Hub",
    },
    {
        "eyebrow": "....And Lots More",
        "accent": ft.Colors.INDIGO_700,
        "icon_bg": ft.Colors.INDIGO_100,
        "icon": ft.Icons.PLAY_CIRCLE_ROUNDED,
        "image": "icon.png",  # e.g. "/assets/onboarding/continue.png"
        "title": "Pick up right\nwhere you left off",
        "body": "Your dashboard remembers your last lesson so you never "
                "lose your place.",
    },
]

ONBOARDING_AUTO_SECONDS = 4.5

# DEV MOCK TOGGLE ------------------------------------------------------------
# Force-show or force-hide the onboarding overlay for testing, bypassing the
# real/mock first-login check below.
#   True  -> always show it (handy while designing/testing)
#   False -> never show it
#   None  -> use check_is_first_login()'s result (the "real" behavior)
FORCE_SHOW_ONBOARDING = None


async def check_is_first_login(page: ft.Page) -> bool:
    """MOCK — swap this out for the real check.

    e.g. read a `has_seen_onboarding` flag off the user record returned by
    your auth/user API, instead of a local device flag.
    """
    user_data  = page.session.store.get("current_user") 
    streak = user_data.get("streak", 0)
    seen = streak >2
    return not seen


async def mark_onboarding_seen(page: ft.Page) -> None:
    """MOCK — swap this out for the real write (API call, DB update, etc.)."""
    await page.shared_preferences.set("has_seen_onboarding", True)


def build_onboarding_overlay(page: ft.Page, on_dismiss) -> ft.Container:
    """Auto-sliding welcome carousel meant to sit on top of the dashboard
    on first login. Calls `on_dismiss()` once the user skips or finishes.
    """
    state = {"index": 0, "auto_task": None, "dismissed": False}
    n_slides = len(ONBOARDING_SLIDES)

    # ── adaptive sizing ────────────────────────────────────────────────
    # Card is capped at 440px so it doesn't stretch absurdly wide on
    # desktop/tablet, but shrinks to fit narrow phone screens with margin.
    CARD_MAX_WIDTH = 800
    CARD_MIN_WIDTH = 280
    CARD_H_PADDING = 30      # matches padding.left/right

    CARD_MAX_HEIGHT = 565  # ceiling: don't let it stretch into a full page on tall/desktop windows
    CARD_MIN_HEIGHT = 420    # floor: enough room for title + progress row + body without clipping
    CARD_V_PADDING = 48      # top/bottom safe margin (status bar, nav, window chrome)

    CARD_SPACING = 6

    def card_width() -> float:
        w = page.width or 390
        return max(CARD_MIN_WIDTH, min(CARD_MAX_WIDTH, w - CARD_H_PADDING))

    def card_height() -> float:
        h = page.height or 550
        return max(CARD_MIN_HEIGHT, min(CARD_MAX_HEIGHT, h - CARD_V_PADDING))

    def segment_width() -> float:
        content_w = card_width() - (CARD_H_PADDING * 2)
        spacing_total = CARD_SPACING * (n_slides - 1)
        return max(0.0, (content_w - spacing_total) / n_slides)

    # ── progress segments — a track + a single fill Container. We only
    # ever set a *target* width and let Flet/Flutter animate the change
    # itself (one smooth transition), instead of us stepping the value
    # in a loop, which is what caused the jerky/irregular fill before.
    fills = []
    segments = []
    for _ in ONBOARDING_SLIDES:
        fill = ft.Container(height=4, border_radius=3, bgcolor=ft.Colors.PRIMARY, width=0)
        track = ft.Container(
            expand=True, height=4, border_radius=3,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE),
            alignment=ft.Alignment.CENTER_LEFT,
            content=fill,
        )
        fills.append(fill)
        segments.append(track)
    progress_row = ft.Row(spacing=CARD_SPACING, controls=segments)

    def set_progress_static():
        w = segment_width()
        for i, fill in enumerate(fills):
            fill.animate = None
            fill.width = w if i < state["index"] else 0

    # ── dots ─────────────────────────────────────────────────────────────
    def handle_dot_tap(i):
        def handler(e):
            go_to(i)
        return handler

    dots = []
    for i in range(n_slides):
        dots.append(
            ft.Container(
                width=7, height=7, border_radius=4,
                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ink=True,
                on_click=handle_dot_tap(i),
            )
        )
    dots_row = ft.Row(spacing=7, controls=dots)

    def refresh_dots():
        for i, d in enumerate(dots):
            active = i == state["index"]
            d.width = 20 if active else 7
            d.bgcolor = ft.Colors.PRIMARY if active else ft.Colors.with_opacity(
                0.15, ft.Colors.ON_SURFACE
            )

    # ── slide content ───────────────────────────────────────────────────
    def build_slide_content(i):
        slide = ONBOARDING_SLIDES[i]
        if slide.get("image"):
            art = ft.Container(
                height=190, alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src=slide["image"], height=float("inf"), width=float("inf"),
                    fit=ft.BoxFit.FIT_WIDTH, border_radius=16,
                ),
            )
        else:
            art = ft.Container(
                height=210, alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=130, height=130, border_radius=65,
                    bgcolor=slide["icon_bg"],
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(slide["icon"], size=54, color=slide["accent"]),
                ),
            )
        return ft.Column(
            key=str(i),
            spacing=10,
            controls=[
                art,
                ft.Text(slide["eyebrow"], size=11.5, weight=ft.FontWeight.W_700,
                         color=slide["accent"]),
                ft.Text(slide["title"], size=21, weight=ft.FontWeight.W_800,
                         color=ft.Colors.ON_SURFACE),
                ft.Text(slide["body"], size=13.5, color=ft.Colors.GREY_500),
            ],
        )

    slide_switcher = ft.AnimatedSwitcher(
        content=build_slide_content(0),
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=300,
    )

    # Wrap the slide area in a GestureDetector so it can be swiped, not
    # just advanced via the Next button.
    def handle_drag_end(e):
        velocity = getattr(e, "primary_velocity", 0) or 0
        if velocity < -200:       # swipe left -> forward
            advance_or_dismiss()
        elif velocity > 200:      # swipe right -> back
            go_to(state["index"] - 1)

    slide_gesture = ft.GestureDetector(
        content=slide_switcher,
        on_horizontal_drag_end=handle_drag_end,
    )

    # ── next / skip controls ────────────────────────────────────────────
    next_label = ft.Text("Next", size=14.5, weight=ft.FontWeight.W_700,
                          color=ft.Colors.SURFACE)
    next_icon = ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=16,
                         color=ft.Colors.SURFACE)
    next_btn = ft.Container(
        bgcolor=ft.Colors.ON_SURFACE,
        border_radius=26,
        padding=ft.Padding.symmetric(horizontal=22, vertical=13),
        ink=True,
        content=ft.Row(spacing=8, tight=True, controls=[next_label, next_icon]),
    )
    skip_btn = ft.TextButton(
        "Skip", style=ft.ButtonStyle(color=ft.Colors.GREY_500)
    )

    # ── navigation / auto-advance ───────────────────────────────────────
    def go_to(index: int, restart_auto: bool = True):
        index = max(0, min(n_slides - 1, index))
        state["index"] = index
        slide_switcher.content = build_slide_content(index)
        set_progress_static()
        refresh_dots()
        is_last = index == n_slides - 1
        next_label.value = "Get started" if is_last else "Next"
        next_btn.bgcolor = ft.Colors.PRIMARY if is_last else ft.Colors.ON_SURFACE
        page.update()
        if restart_auto:
            start_auto()

    async def auto_loop():
        idx = state["index"]
        fill = fills[idx]
        target = segment_width()

        # snap to 0 with no animation, then animate to full width in one
        # continuous transition — this is what makes the fill smooth.
        fill.animate = None
        fill.width = 0
        page.update()
        await asyncio.sleep(0.02)  # let the 0-width frame render first
        if state["dismissed"] or state["index"] != idx:
            return
        fill.animate = ft.Animation(int(ONBOARDING_AUTO_SECONDS * 1000), ft.AnimationCurve.LINEAR)
        fill.width = target
        page.update()

        try:
            await asyncio.sleep(ONBOARDING_AUTO_SECONDS)
            if state["dismissed"] or state["index"] != idx:
                return
            if idx == n_slides - 1:
                return
            go_to(idx + 1)
        except asyncio.CancelledError:
            pass

    def start_auto():
        if state["auto_task"]:
            state["auto_task"].cancel()
        state["auto_task"] = page.run_task(auto_loop)

    async def dismiss_async():
        state["dismissed"] = True
        if state["auto_task"]:
            state["auto_task"].cancel()
        await mark_onboarding_seen(page)
        on_dismiss()

    def advance_or_dismiss():
        if state["index"] == n_slides - 1:
            page.run_task(dismiss_async)
        else:
            go_to(state["index"] + 1)

    def handle_next(e):
        advance_or_dismiss()

    def handle_skip(e):
        go_to(n_slides - 1)

    next_btn.on_click = handle_next
    skip_btn.on_click = handle_skip

    card_container = ft.SafeArea(content=ft.Container(
        bgcolor=ft.Colors.ON_PRIMARY,
        border_radius=28,
        width=card_width(),
        height=card_height(),
        padding=ft.Padding.only(
            left=CARD_H_PADDING, right=CARD_H_PADDING, top=18, bottom=50
        ),
        content=ft.Column(
            spacing=14,
            controls=[
                progress_row,
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[skip_btn]),
                slide_gesture,
                ft.Container(height=28),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[dots_row, next_btn],
                ),
            ],
        ),
    )
    )
    # Re-fit the card (and the progress fill widths) if the window/screen
    # size changes, so this isn't locked to one phone viewport.
    # NOTE: chains onto any pre-existing page.on_resized handler so we
    # don't clobber other resize logic elsewhere in the app.
    previous_on_resized = page.on_resize

    def recompute_sizing(e=None):
        card_container.width = card_width()
        w = segment_width()
        for i, fill in enumerate(fills):
            fill.animate = None
            fill.width = w if i <= state["index"] else 0
        page.update()
        if previous_on_resized:
            previous_on_resized(e)

    page.on_resized = recompute_sizing

    set_progress_static()
    refresh_dots()

    overlay = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
        alignment=ft.Alignment.CENTER,
        content=card_container,
    )

    start_auto()
    return overlay


# ─────────────────────────────────────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────────────────────────────────────
async def dashboard_view(page: ft.Page):
    app_bar = get_bottom_appbar(page)

    content_socket = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(color=ft.Colors.PRIMARY, stroke_width=3)
    )

    # ── onboarding overlay (lives inside the View's body via a Stack, so it
    # only covers the main page content — the bottom app bar is a separate
    # Scaffold slot and sits outside this Stack, so it's never covered) ─────
    onboarding_slot = ft.Container(
        expand=True,
        visible=False,
        opacity=0,
        scale=0.96,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        data="onboarding_overlay",
    )

    async def hide_onboarding_async():
        # fade + shrink out, then actually remove it once the animation's done
        bottom_appbar.opacity=1
        onboarding_slot.opacity = 0
        onboarding_slot.scale = 0.96
        page.update()
        await asyncio.sleep(0.4)
        onboarding_slot.visible = False
        onboarding_slot.content = None
        page.update()

    def hide_onboarding():
        page.run_task(hide_onboarding_async)

    async def maybe_show_onboarding():
        # FORCE_SHOW_ONBOARDING (defined near ONBOARDING_SLIDES above) wins
        # when set to True/False, for quick manual testing. Set it to None
        # to fall back to the real/mock check_is_first_login() result.
        seen = await page.shared_preferences.get('has_seen_onboarding')
        print(seen)
        if FORCE_SHOW_ONBOARDING is not None:
            should_show = FORCE_SHOW_ONBOARDING
        elif not seen:
            should_show = await check_is_first_login(page) 
        else:
            return

        if not should_show:
            return

        # let the dashboard render and settle first — this is what makes the
        # overlay feel like it eases in over an already-loaded page instead
        # of slamming in before anything underneath is visible
        await asyncio.sleep(1.5)
        bottom_appbar.opacity= 0.5
        page.update()
        onboarding_slot.content = build_onboarding_overlay(
            page, on_dismiss=hide_onboarding
        )
        onboarding_slot.visible = True
        page.update()
        await asyncio.sleep(0.03)  # let the 0-opacity/0.96-scale frame render first
        onboarding_slot.opacity = 1
        onboarding_slot.scale = 1
        page.update()

    page.run_task(maybe_show_onboarding)

    # ── greeting text (mutated after data loads) ──────────────────────────────
    greeting_name = ft.Text(
        "",
        size=24, weight=ft.FontWeight.W_900, color=ft.Colors.SURFACE,
    )
    greeting_sub = ft.Text(
        get_random_quote(),
        size=12, color=ft.Colors.with_opacity(0.75, ft.Colors.SURFACE),
        italic=True,
        opacity=0,
        offset=ft.Offset(0, 0.3),
        animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
    )
    
    # ── tips text ─────────────────────────────────────────────────────────────
    tip_container = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        border_radius=ft.BorderRadius.all(12),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        opacity=0,
        animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
        content=ft.Row(
            wrap=True,
            spacing=8,
            controls=[
                ft.Text(
                    f'💡{get_random_tip()}',
                    size=11, color=ft.Colors.with_opacity(0.9, ft.Colors.SURFACE)
                )
            ]
        )
    )

    # ── stats variables (mutated after data loads) ────────────────────────────
    stat_enrolled = ft.Text("-", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.SURFACE)
    stat_finished = ft.Text("-", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.SURFACE)
    stat_streak = ft.Text("-", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.SURFACE)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. HEADER / HERO
    # ─────────────────────────────────────────────────────────────────────────
    def _stat_col(value_text: ft.Text, label: str):
        return ft.Column(
            spacing=2,
            controls=[
                value_text,
                ft.Text(label, size=11, color=ft.Colors.with_opacity(0.85, ft.Colors.SURFACE)),
            ]
        )

    header = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.PRIMARY, "#1a3b5c"], # Using PRIMARY and a deep complementary blue
        ),
        width=float("inf"),
        border_radius=16,
        padding=ft.Padding.all(24),
        margin=ft.Padding.only(left=20, right=20, top=14, bottom=22),
        opacity=0,
        offset=ft.Offset(0, 0.2),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        content=ft.Column(
            spacing=20,
            controls=[
                ft.Column(
                    spacing=6,
                    controls=[greeting_name, greeting_sub, tip_container],
                ),
                ft.Row(
                    wrap=True,
                    spacing=16,
                    run_spacing=16,
                    controls=[
                        _stat_col(stat_enrolled, "Active Courses"),
                        _stat_col(stat_finished, "Finished Courses"),
                        _stat_col(stat_streak, "Day Streak"),
                    ]
                )
            ],
        ),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. QUICK-ACTION TILES
    # ─────────────────────────────────────────────────────────────────────────
    def quick_tile(icon, label, sublabel, bg, fg, route):
        return ft.Container(
            expand=True,
            bgcolor=bg,
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            ink=True,
            on_click=lambda _, r=route: page.go(r),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 3),
            ),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Container(
                        width=38, height=38,
                        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.SURFACE),
                        border_radius=10,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, color=ft.Colors.SURFACE, size=20),
                    ),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_700,
                            color=ft.Colors.SURFACE),
                    ft.Text(sublabel, size=10,
                            color=ft.Colors.with_opacity(0.8, ft.Colors.SURFACE)),
                ],
            ),
        )

    quick_actions = ft.Row(
        spacing=12,
        opacity=0,
        offset=ft.Offset(0, 0.2),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        controls=[
            quick_tile(
                ft.Icons.LIBRARY_BOOKS_ROUNDED,
                "Courses", "Browse library",
                ft.Colors.INDIGO_300, ft.Colors.SURFACE,
                "/courses",
            ),
            quick_tile(
                ft.Icons.PEOPLE_ALT_ROUNDED,
                "Network", "Connect & study",
                ft.Colors.TEAL_400, ft.Colors.SURFACE,
                "/network",
            ),
        ],
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. FRIENDS SECTION
    # ─────────────────────────────────────────────────────────────────────────
    def friend_avatar(name: str, ):
        initials = "".join(p[0].upper() for p in name.split()[:2])
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            controls=[
                ft.Stack(
                    controls=[
                        ft.CircleAvatar(
                            content=ft.Text(initials, size=13,
                                            weight=ft.FontWeight.W_700),
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            color=ft.Colors.ON_PRIMARY_CONTAINER,
                            radius=24,
                        )
                    ],
                ),
                ft.Text(name.split()[0], size=10, color=ft.Colors.GREY_600,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
        )

    # placeholder friends — replace with real API data
    token = await page.shared_preferences.get("auth_token")
    friends = await get_all_users(token)

    friends_row = ft.Row(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            # Add-friend button
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=[
                    ft.Container(
                        width=48, height=48,
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=24,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _: page.go("/network"),
                        content=ft.Icon(ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                                        color=ft.Colors.PRIMARY, size=20),
                    ),
                    ft.Text("Add", size=10, color=ft.Colors.PRIMARY),
                ],
            ),
            *[
    friend_avatar(friend["name"] if isinstance(friend["name"], str) else "unknown")
    for friend in friends
],
        ],
    )

    friends_card = _card(
        ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.PEOPLE_ALT_ROUNDED,
                                    color=ft.Colors.TEAL_500, size=18),
                            ft.Text("Friends", size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=ft.Colors.ON_SURFACE),
                        ]),
                        ft.TextButton(
                            "See All",
                            on_click=lambda _: page.go("/network"),
                            style=ft.ButtonStyle(
                                color=ft.Colors.PRIMARY,
                                padding=ft.Padding.all(0),
                            ),
                        ),
                    ],
                ),
                friends_row,
            ],
        )
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. SELF-STUDY SECTION
    # ─────────────────────────────────────────────────────────────────────────
    def study_mode_tile(icon, title, desc, route, bg, fg):
        return ft.Container(
            expand=True,
            bgcolor=bg,
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            ink=True,
            on_click=lambda _, r=route: page.go(r),
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Container(
                        width=36, height=36,
                        bgcolor=fg,
                        border_radius=10,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, size=18, color=ft.Colors.SURFACE),
                    ),
                    ft.Text(title, size=11, weight=ft.FontWeight.W_700,
                            color=ft.Colors.SURFACE),
                    ft.Text(desc, size=10, color=ft.Colors.SURFACE,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
            ),
        )

    self_study_card = _card(
        ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.SELF_IMPROVEMENT_ROUNDED,
                                    color=ft.Colors.PURPLE_400, size=18),
                            ft.Text("Self-Study", size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=ft.Colors.ON_SURFACE),
                        ]),
                        ft.TextButton(
                            "Explore",
                            on_click=lambda _: page.go("/self-study"),
                            style=ft.ButtonStyle(
                                color=ft.Colors.PRIMARY,
                                padding=ft.Padding.all(0),
                            ),
                        ),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        study_mode_tile(
                            ft.Icons.QUIZ_ROUNDED,
                            "Quick Quiz",
                            "Test what you know",
                            "/self-study",
                            ft.Colors.PURPLE_400,
                            ft.Colors.PURPLE_300,
                        ),
                        study_mode_tile(
                            ft.Icons.HISTORY_EDU_ROUNDED,
                            "Exam Prep",
                            "Revise & practice",
                            "/self-study",
                            ft.Colors.ORANGE_400,
                            ft.Colors.ORANGE_300,
                        ),
                        study_mode_tile(
                            ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                            "Flashcards",
                            "Spaced repetition",
                            "/self-study",
                            ft.Colors.TEAL_400,
                            ft.Colors.TEAL_300,
                        ),
                    ],
                ),
            ],
        )
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. ACTIVITY CHART
    # ─────────────────────────────────────────────────────────────────────────
    chart_holder = ft.Container(
        height=180,
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.ProgressRing(color=ft.Colors.PRIMARY, width=20, height=20),
                ft.Text("Syncing activity…", size=13, color=ft.Colors.GREY_400),
            ],
        ),
    )

    activity_card = _card(
        ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.ANALYTICS_OUTLINED,
                                    color=ft.Colors.PRIMARY, size=18),
                            ft.Text("Weekly Activity", size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=ft.Colors.ON_SURFACE),
                        ]),
                    ],
                ),
                chart_holder,
            ],
        )
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. CONTINUE LEARNING
    # ─────────────────────────────────────────────────────────────────────────
    continue_learning_section = ft.Container(
        width=float("inf"),
        opacity=0,
        offset=ft.Offset(0, 0.2),
        animate_opacity=ft.Animation(400, ft.AnimationCurve.DECELERATE),
        animate_offset=ft.Animation(400, ft.AnimationCurve.DECELERATE),
    )   # swapped in after data loads

    # ─────────────────────────────────────────────────────────────────────────
    # 8. DATA FETCHER
    # ─────────────────────────────────────────────────────────────────────────
    async def fetch_dashboard_data():
        # ── user greeting & stats ─────────────────────────────────────────────
        user_data  = page.session.store.get("current_user") or {}
        first_name = user_data.get("first_name", "there")
        target_greeting = f"{get_random_greeting()} {first_name}!"

        # Trigger fade animations immediately
        greeting_sub.opacity = 1
        greeting_sub.offset = ft.Offset(0, 0)
        tip_container.opacity = 1
        page.update()

        # Typing animation
        async def type_greeting(target_text: str):
            current_text = ""
            for char in target_text:
                current_text += char
                greeting_name.value = current_text + "|"
                page.update()
                await asyncio.sleep(0.04)
            
            # Blink the cursor a few times
            for _ in range(3):
                greeting_name.value = current_text + " "
                page.update()
                await asyncio.sleep(0.4)
                greeting_name.value = current_text + "|"
                page.update()
                await asyncio.sleep(0.4)
                
            # Remove cursor
            greeting_name.value = current_text
            page.update()

        page.run_task(type_greeting, target_greeting)
        
        streak = user_data.get("streak", 0)

        token = await page.shared_preferences.get("auth_token")

        # ── enrollments (non-fatal on failure) ────────────────────────────────
        try:
            enrolled_list = await asyncio.wait_for(
                get_enrollments(token, None), timeout=15
            )
            if not isinstance(enrolled_list, list):
                enrolled_list = []
        except (asyncio.TimeoutError, Exception):
            enrolled_list = []
            
        active_count = len(enrolled_list)
        finished_count = sum(1 for c in enrolled_list if c.get("progress", 0.0) >= 100)
        
        # ── stat animation ────────────────────────────────────────────────────
        async def animate_stats(target_act: int, target_fin: int, target_str: int):
            # Find the max so we know how many steps to take if we want to run together
            max_val = max(target_act, target_fin, target_str)
            if max_val == 0:
                stat_enrolled.value = "0"
                stat_finished.value = "0"
                stat_streak.value = "0"
                page.update()
                return

            # Animate in ~20 steps or max_val steps, whichever is smaller, over ~600ms
            steps = min(max_val, 15)
            delay = 0.3 / steps

            for step in range(1, steps + 1):
                cur_act = int((target_act / steps) * step)
                cur_fin = int((target_fin / steps) * step)
                cur_str = int((target_str / steps) * step)
                
                stat_enrolled.value = str(cur_act)
                stat_finished.value = str(cur_fin)
                stat_streak.value = str(cur_str)
                page.update()
                await asyncio.sleep(delay)
                
            # Final snap to exact values
            stat_enrolled.value = str(target_act)
            stat_finished.value = str(target_fin)
            stat_streak.value = str(target_str)
            page.update()

        page.run_task(animate_stats, active_count, finished_count, streak)

        # ── build continue-learning cards ─────────────────────────────────────
        enrolled_cards = []
        for course in enrolled_list:
            if course.get("progress", 0) < 100:
                course_id   = course.get("id")
                course_name = course.get("name", "Untitled Course")
                progress    = course.get("progress", 0.0)
                card        = get_continue_learning_card(course_name, progress, course_id, page)
                card.on_click = lambda e, cid=course_id: page.go(f"/courses/{cid}/view")
                enrolled_cards.append(card)

        if enrolled_cards:
            continue_learning_section.content = ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(spacing=8, controls=[
                                ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED,
                                        color=ft.Colors.PRIMARY, size=18),
                                ft.Text("Continue Learning", size=16,
                                        weight=ft.FontWeight.W_700,
                                        color=ft.Colors.ON_SURFACE),
                            ]),
                            ft.TextButton(
                                "View All",
                                on_click=lambda _: page.go("/courses"),
                                style=ft.ButtonStyle(color=ft.Colors.PRIMARY,
                                                     padding=ft.Padding.all(0)),
                            ),
                        ],
                    ),
                    ft.Row(
                        scroll=ft.ScrollMode.AUTO,
                        spacing=14,
                        controls=enrolled_cards,
                    ),
                ],
            )
        else:
            continue_learning_section.content = ft.Container(
                bgcolor=ft.Colors.SURFACE,
                border_radius=16,
                border=ft.Border.all(1, ft.Colors.GREY_200),
                padding=18,
                shadow=ft.BoxShadow(
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                    offset=ft.Offset(0, 3),
                ),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.SCHOOL_OUTLINED, size=36,
                                color=ft.Colors.GREY_300),
                        ft.Text("No courses in progress.",
                                size=13, color=ft.Colors.GREY_400),
                        ft.TextButton(
                            "Find a course →",
                            on_click=lambda _: page.go("/courses"),
                            style=ft.ButtonStyle(color=ft.Colors.PRIMARY),
                        ),
                    ],
                )
            )

        # ── weekly activity chart ─────────────────────────────────────────────
        try:
            today  = datetime.now()
            monday = today - timedelta(days=today.weekday())

            week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            week_labels[today.weekday()] = "Today"

            activity_data = []
            conn = sqlite3.connect("lms_local.db")
            cur  = conn.cursor()
            for i in range(7):
                target = monday + timedelta(days=i)
                if target.date() > today.date():
                    activity_data.append(0)
                else:
                    cur.execute(
                        "SELECT activity_count FROM daily_activity WHERE date = ?",
                        (target.strftime("%Y-%m-%d"),),
                    )
                    res = cur.fetchone()
                    activity_data.append(res[0] if res else 0)
            conn.close()

            chart_max_y = max(activity_data) + 2 if max(activity_data) > 0 else 10

            weekly_chart = fch.BarChart(
                max_y=chart_max_y,
                groups=[
                    fch.BarChartGroup(
                        x=i,
                        rods=[
                            fch.BarChartRod(
                                from_y=0, to_y=val,
                                color=ft.Colors.PRIMARY if week_labels[i] != "Today"
                                      else ft.Colors.SECONDARY,
                                width=18,
                                border_radius=6,
                            )
                        ],
                    )
                    for i, val in enumerate(activity_data)
                ],
                bottom_axis=fch.ChartAxis(
                    labels=[
                        fch.ChartAxisLabel(
                            value=i,
                            label=ft.Text(
                                week_labels[i], size=10,
                                color=ft.Colors.PRIMARY
                                      if week_labels[i] == "Today"
                                      else ft.Colors.GREY_400,
                                weight=ft.FontWeight.W_700
                                       if week_labels[i] == "Today"
                                       else ft.FontWeight.NORMAL,
                            ),
                        )
                        for i in range(7)
                    ]
                ),
                horizontal_grid_lines=fch.ChartGridLines(
                    color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                    width=1,
                    dash_pattern=[4, 4],
                ),
                tooltip=fch.BarChartTooltip(
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
                ),
                interactive=True,
                expand=True,
            )
            chart_holder.content = weekly_chart

        except Exception:
            # Chart failure is non-fatal — show a quiet fallback
            chart_holder.content = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.BAR_CHART_ROUNDED,
                            size=32, color=ft.Colors.GREY_300),
                    ft.Text("Activity data unavailable.",
                            size=12, color=ft.Colors.GREY_400),
                ],
            )

        content_socket.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                    controls=[
                        header,
                        ft.Container(
                            padding=ft.Padding.symmetric(
                                horizontal=16, vertical=16
                            ),
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    quick_actions,
                                    friends_card,
                                    activity_card,
                                    continue_learning_section,
                                    self_study_card,
                                    ft.Container(height=16),
                                ],
                            ),
                        )
                    ],
                ),
            ],
        )
        page.update()
        
        # Trigger staggered fade-up animations for main dashboard sections
        sections_to_animate = [
            header,
            quick_actions, 
            friends_card, 
            activity_card, 
            continue_learning_section, 
            self_study_card
        ]
        
        for idx, section in enumerate(sections_to_animate):
            async def animate_section(s, i):
                await asyncio.sleep(i * 0.1)
                s.opacity = 1
                s.offset = ft.Offset(0, 0)
                page.update()
            
            page.run_task(animate_section, section, idx)

    page.run_task(fetch_dashboard_data)

    # ─────────────────────────────────────────────────────────────────────────
    # VIEW
    # ─────────────────────────────────────────────────────────────────────────
    return ft.View(
        route="/dashboard",
        bottom_appbar=app_bar,
        bgcolor=ft.Colors.ON_PRIMARY,
        padding=0,
        controls=[
            ft.Stack(
                expand=True,
                controls=[
                    ft.SafeArea(
                        expand=True,
                        content=content_socket,
                    ),
                    # Onboarding sits on top of the page content only —
                    # the bottom app bar is a separate Scaffold slot outside
                    # this Stack, so it's never covered by the overlay.
                    onboarding_slot,
                ],
            ),
        ],
    )