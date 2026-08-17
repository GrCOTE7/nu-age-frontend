import flet as ft

from src.components.bottom_appbar import get_bottom_appbar
from src.requests.playlists import get_playlist, update_playlist

# =========================================================
# SECTION 1: CONSTANTS
# =========================================================
_BORDER_RADIUS = 12
_SECTION_SPACING = 20
_INPUT_STYLE = {
    "border_color": ft.Colors.OUTLINE_VARIANT,
    "focused_border_color": ft.Colors.PRIMARY,
    "border_radius": _BORDER_RADIUS,
}

# =========================================================
# SECTION 2: MAIN VIEW FUNCTION
# =========================================================
async def playlist_settings_view(page: ft.Page, playlist_id: str) -> ft.View:

    # ── Auth token ────────────────────────────────────────────────────────────
    try:
        token = await page.shared_preferences.get("auth_token")
        if not token:
            raise ValueError("Missing auth token")
    except Exception:
        return _error_view(playlist_id, "Authentication failed. Please log in again.")

    # =========================================================
    # SECTION 3: API WRAPPERS (with error handling)
    # =========================================================
    async def _save_setting(key: str, value) -> bool:
        try:
            res = await update_playlist(token, playlist_id, {key: value})
            if isinstance(res, dict) and "error" in res:
                _log_error(f"save_setting:{key}", Exception(res["error"]))
                return False
            return True
        except Exception as ex:
            _log_error(f"save_setting:{key}", ex)
            return False

    # ── Fetch core playlist data ────────────────────────────────────────────────
    try:
        playlist_data = await get_playlist(token, playlist_id)
        if isinstance(playlist_data, dict) and "error" in playlist_data:
            playlist_data = None
    except Exception as ex:
        _log_error("get_playlist", ex)
        playlist_data = None

    if not playlist_data:
        return _error_view(playlist_id, "Playlist not found or could not be loaded.")

    org_id = playlist_data.get("org_id", "")

    # =========================================================
    # SECTION 4: SHARED UI HELPERS
    # =========================================================
    bottom_bar = get_bottom_appbar(page)

    content_socket = ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),
        content=ft.ProgressRing(color=ft.Colors.PRIMARY),
    )

    def show_toast(message: str, color=ft.Colors.GREEN_700):
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.ON_PRIMARY),
            bgcolor=color,
            duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def show_error_toast(message: str):
        show_toast(message, color=ft.Colors.RED_700)

    def _save_btn(on_click_fn) -> ft.ElevatedButton:
        """Factory for uniform Save buttons."""
        return ft.ElevatedButton(
            content=ft.Text("Save", color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.W_600),
            bgcolor=ft.Colors.PRIMARY,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=on_click_fn,
        )

    def _set_btn_loading(btn: ft.ElevatedButton):
        btn.disabled = True
        btn.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.ON_PRIMARY)
        page.update()

    def _set_btn_done(btn: ft.ElevatedButton, label="Save"):
        btn.disabled = False
        btn.content = ft.Text(label, color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.W_600)
        page.update()

    def create_section(
        title: str,
        description: str,
        content: ft.Control,
        is_danger: bool = False,
    ) -> ft.Container:
        title_color    = ft.Colors.RED_700 if is_danger else ft.Colors.ON_SURFACE
        border_color   = ft.Colors.RED_200 if is_danger else ft.Colors.OUTLINE_VARIANT
        return ft.Container(
            bgcolor=ft.Colors.SURFACE,
            border_radius=15,
            padding=20,
            border=ft.Border.all(1, border_color),
            content=ft.Column(
                spacing=15,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(title, size=16, weight=ft.FontWeight.W_700, color=title_color),
                            ft.Text(description, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                    ),
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    content,
                ],
            ),
        )

    # =========================================================
    # SECTION 5: GENERAL SETTINGS
    # =========================================================
    name_input = ft.TextField(
        value=playlist_data.get("name", ""),
        label="Playlist Name",
        expand=True,
        **_INPUT_STYLE,
    )
    
    desc_input = ft.TextField(
        value=playlist_data.get("description", ""),
        label="Description",
        multiline=True,
        min_lines=2,
        expand=True,
        **_INPUT_STYLE,
    )

    async def save_name(e):
        btn = e.control
        name = name_input.value.strip()
        if not name:
            show_error_toast("Playlist name cannot be empty.")
            return
        _set_btn_loading(btn)
        ok = await _save_setting("name", name)
        _set_btn_done(btn)
        show_toast("Playlist name updated.") if ok else show_error_toast("Failed to update playlist name.")

    async def save_desc(e):
        btn = e.control
        desc = desc_input.value.strip()
        _set_btn_loading(btn)
        ok = await _save_setting("description", desc)
        _set_btn_done(btn)
        show_toast("Description updated.") if ok else show_error_toast("Failed to update description.")


    save_name_btn = _save_btn(lambda e: page.run_task(save_name, e))
    save_desc_btn = _save_btn(lambda e: page.run_task(save_desc, e))

    general_section = create_section(
        title="General Information",
        description="Update the foundational details of this playlist.",
        content=ft.Column(
            spacing=15,
            controls=[
                ft.Row([name_input, save_name_btn]),
                ft.Row([desc_input, save_desc_btn]),
            ],
        ),
    )

    # =========================================================
    # SECTION 6: ACCESS CONTROLS
    # =========================================================
    public_val = str(playlist_data.get("is_public", "false")).lower()
    public_radio = ft.RadioGroup(
        value=public_val,
        content=ft.Row(
            wrap=True,
            controls=[
                ft.Radio(value="false",        label="Private / Organization", fill_color=ft.Colors.PRIMARY),
                ft.Radio(value="true",         label="Public",       fill_color=ft.Colors.PRIMARY),
            ],
        ),
    )

    async def save_public(e):
        btn = e.control
        _set_btn_loading(btn)
        # Convert string to bool
        val = public_radio.value == "true"
        ok = await _save_setting("is_public", val)
        _set_btn_done(btn)
        show_toast("Visibility updated.") if ok else show_error_toast("Failed to update visibility.")

    save_public_btn = _save_btn(lambda e: page.run_task(save_public, e))

    access_section = create_section(
        title="Access",
        description="Control who can view this playlist.",
        content=ft.Column(
            spacing=20,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=4,
                            controls=[
                                ft.Text("Playlist Visibility", weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE),
                                public_radio,
                            ],
                        ),
                        save_public_btn,
                    ],
                ),
            ],
        ),
    )

    # =========================================================
    # SECTION 7: CURRICULUM
    # =========================================================
    curriculum_section = create_section(
        title="Curriculum",
        description="Add, remove, or reorder courses in this playlist.",
        content=ft.ElevatedButton(
            "Open Curriculum Builder",
            width=float("inf"),
            icon=ft.Icons.LIST_ROUNDED,
            icon_color=ft.Colors.ON_SURFACE,
            color=ft.Colors.ON_SURFACE,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda _: page.go(f"/playlists/{playlist_id}/build"),
        ),
    )

    # =========================================================
    # SECTION 8: LAYOUT ASSEMBLY
    # =========================================================
    async def load_initial_data():
        header = ft.Container(
            bgcolor=ft.Colors.PRIMARY,
            height=85,
            border_radius=ft.BorderRadius(
                top_left=0, top_right=0, bottom_left=30, bottom_right=30
            ),
            padding=ft.Padding(top=10, left=15, right=25, bottom=15),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK_ROUNDED,
                        icon_color=ft.Colors.ON_PRIMARY,
                        on_click=lambda _: page.go("/organisations"),
                    ),
                    ft.Text(
                        "Playlist Settings",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_PRIMARY,
                    ),
                    ft.Container(width=40),  # balance the back button
                ],
            ),
        )

        final_layout = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                ft.Container(
                    expand=True,
                    padding=ft.Padding.all(20),
                    content=ft.Column(
                        scroll=ft.ScrollMode.AUTO,
                        spacing=_SECTION_SPACING,
                        controls=[
                            general_section,
                            access_section,
                            curriculum_section,
                            ft.Container(height=20),
                        ],
                    ),
                ),
            ],
        )

        content_socket.alignment = None
        content_socket.content   = final_layout
        page.update()

    page.run_task(load_initial_data)

    return ft.View(
        route=f"/playlists/{playlist_id}/settings",
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        padding=0,
        bottom_appbar=bottom_bar,
        controls=[
            ft.SafeArea(
                expand=True,
                content=content_socket,
            )
        ],
    )


# =========================================================
# SECTION 9: UTILITIES
# =========================================================
def _error_view(playlist_id: str, message: str) -> ft.View:
    return ft.View(
        route=f"/playlists/{playlist_id}/settings",
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED,
                                size=52, color=ft.Colors.ERROR),
                        ft.Text(message, color=ft.Colors.ERROR, size=16,
                                text_align=ft.TextAlign.CENTER),
                    ],
                ),
            )
        ],
    )

def _log_error(context: str, ex: Exception):
    print(f"[ERROR] [{context}] {type(ex).__name__}: {ex}")
