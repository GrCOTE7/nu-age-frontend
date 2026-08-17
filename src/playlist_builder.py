import flet as ft
import asyncio
from src.requests.playlists import (
    get_playlist,
    add_courses_to_playlist,
    remove_course_from_playlist,
    reorder_playlist_course,
    get_playlist_analytics,
    save_bulk_playlist_courses
)
from src.requests.organisations import get_organisation_courses

UI_ACCENT = ft.Colors.PRIMARY

async def playlist_builder_view(page: ft.Page, playlist_id: str):
    token = None
    org_id = page.session.store.get("current_org_id")
    
    # State
    playlist_data = {}
    playlist_courses = []
    local_courses = []  # Local staging list
    org_courses = []
    analytics_data = []

    # Refs
    main_column = ft.Ref[ft.Column]()
    tabs = ft.Ref[ft.Tabs]()
    curriculum_view = ft.Ref[ft.Container]()
    analytics_view = ft.Ref[ft.Container]()

    async def load_data():
        nonlocal playlist_data, playlist_courses, local_courses, org_courses, analytics_data, token
        token = await page.shared_preferences.get("auth_token")
        
        # Load playlist info
        res = await get_playlist(token, playlist_id)
        if "error" not in res:
            playlist_data = res
            raw_courses = res.get("playlist_courses", [])
            playlist_courses = [item.get("course", {}) for item in raw_courses if "course" in item]
            # Initialize local state to match backend
            local_courses = list(playlist_courses)
            
        # Load org courses
        if org_id:
            org_courses = await get_organisation_courses(token, org_id)
        
        # Load analytics
        analytics_data = await get_playlist_analytics(token, playlist_id)

    def build_curriculum_view():
        def render_course_item(c_data, index, total):
            c_id = c_data.get("id")
            c_name = c_data.get("name", "Untitled")
            
            def on_move_up(e):
                if index > 0:
                    local_courses[index], local_courses[index-1] = local_courses[index-1], local_courses[index]
                    curriculum_view.current.content = build_curriculum_view()
                    page.update()
                
            def on_move_down(e):
                if index < total - 1:
                    local_courses[index], local_courses[index+1] = local_courses[index+1], local_courses[index]
                    curriculum_view.current.content = build_curriculum_view()
                    page.update()
                
            def on_remove(e):
                local_courses.pop(index)
                curriculum_view.current.content = build_curriculum_view()
                page.update()
                
            return ft.Card(
                elevation=2,
                margin=ft.Margin.only(bottom=8),
                content=ft.ListTile(
                    leading=ft.CircleAvatar(
                        content=ft.Text(str(index + 1), weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        color=ft.Colors.ON_SURFACE
                    ),
                    title=ft.Text(c_name, weight=ft.FontWeight.BOLD, size=16),
                    trailing=ft.Row(
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.IconButton(ft.Icons.ARROW_UPWARD, disabled=(index == 0), on_click=on_move_up, tooltip="Move Up"),
                            ft.IconButton(ft.Icons.ARROW_DOWNWARD, disabled=(index == total - 1), on_click=on_move_down, tooltip="Move Down"),
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=on_remove, tooltip="Remove from Playlist"),
                        ]
                    )
                )
            )

        items = []
        if local_courses:
            for idx, c in enumerate(local_courses):
                items.append(render_course_item(c, idx, len(local_courses)))
        else:
            items.append(ft.Text("No courses in this playlist yet.", color=ft.Colors.GREY_500))

        add_btn = ft.ElevatedButton(
            "Add Course",
            icon=ft.Icons.ADD,
            bgcolor=UI_ACCENT,
            color=ft.Colors.WHITE,
            on_click=show_add_course_modal
        )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Row([ft.Text("Curriculum", size=20, weight=ft.FontWeight.BOLD), add_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                *items
            ]
        )

    def show_add_course_modal(e):
        selected_course_id = [None]
        
        # Filter out courses already in the local playlist
        existing_ids = [c.get("id") for c in local_courses]
        available = [c for c in org_courses if c.get("id") not in existing_ids]

        dd_options = [ft.dropdown.Option(key=c.get("id"), text=c.get("name")) for c in available]
        
        dd = ft.Dropdown(
            options=dd_options,
            label="Select a course",
            width=300,
            on_select=lambda ev: selected_course_id.__setitem__(0, ev.control.value)
        )

        def on_add_confirm(ev):
            if selected_course_id[0]:
                c_to_add = next((c for c in org_courses if c.get("id") == selected_course_id[0]), None)
                if c_to_add:
                    local_courses.append(c_to_add)
                page.pop_dialog()
                curriculum_view.current.content = build_curriculum_view()
                page.update()

        def on_cancel(ev):
            page.pop_dialog(dlg)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Add Course to Playlist"),
            content=ft.Column([dd], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Add", bgcolor=UI_ACCENT, color=ft.Colors.WHITE, on_click=on_add_confirm)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)
        page.update()

    def build_analytics_view():
        total_enrollments = len(analytics_data) if analytics_data else 0
        completions = sum(1 for e in analytics_data if e.get("progress", 0) == 100)
        in_progress = sum(1 for e in analytics_data if 0 < e.get("progress", 0) < 100)
        not_started = sum(1 for e in analytics_data if e.get("progress", 0) == 0)

        # Progress distribution for simple bar charts
        total_valid = total_enrollments if total_enrollments > 0 else 1
        pct_completed = (completions / total_valid) * 100
        pct_in_progress = (in_progress / total_valid) * 100
        pct_not_started = (not_started / total_valid) * 100

        def stat_card(title, value, color=UI_ACCENT):
            return ft.Card(
                elevation=4,
                content=ft.Container(
                    padding=20,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=12,
                    content=ft.Column([
                        ft.Text(title, size=14, color=ft.Colors.ON_SURFACE),
                        ft.Text(str(value), size=32, weight=ft.FontWeight.BOLD, color=color)
                    ])
                )
            )

        return ft.Column(
            spacing=20,
            controls=[
                ft.Text("Playlist Analytics", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    spacing=20,
                    controls=[
                        stat_card("Total Enrollments", total_enrollments),
                        stat_card("Completions", completions, ft.Colors.GREEN),
                        stat_card("In Progress", in_progress, ft.Colors.BLUE),
                        stat_card("Not Started", not_started, ft.Colors.GREY),
                    ]
                ),
                ft.Card(
                    elevation=2,
                    margin=ft.Margin.only(top=20),
                    content=ft.Container(
                        padding=20,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                        border_radius=12,
                        content=ft.Column([
                            ft.Text("Progress Overview", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.Container(width=pct_completed * 4, height=20, bgcolor=ft.Colors.GREEN, border_radius=4, tooltip=f"Completed: {completions}"),
                                ft.Container(width=pct_in_progress * 4, height=20, bgcolor=ft.Colors.BLUE, border_radius=4, tooltip=f"In Progress: {in_progress}"),
                                ft.Container(width=pct_not_started * 4, height=20, bgcolor=ft.Colors.GREY, border_radius=4, tooltip=f"Not Started: {not_started}"),
                            ], spacing=2) if total_enrollments > 0 else ft.Text("No enrollments to display.", color=ft.Colors.GREY_500)
                        ])
                    )
                )
            ]
        )

    async def refresh_view():
        await load_data()
        curriculum_view.current.content = build_curriculum_view()
        analytics_view.current.content = build_analytics_view()
        page.update()

    async def on_save_curriculum(e):
        course_ids = [c.get("id") for c in local_courses if c.get("id")]
        res = await save_bulk_playlist_courses(token, playlist_id, {"course_ids": course_ids})
        if "error" in res:
            dlg = ft.AlertDialog(title=ft.Text("Error"), content=ft.Text(res["error"]))
            page.show_dialog(dlg)
            page.update()
            return
        
        snack = ft.SnackBar(ft.Text("Curriculum saved successfully!"), bgcolor=ft.Colors.GREEN_700)
        page.overlay.append(snack)
        snack.open=True
        
        # Refresh the baseline state
        await load_data()
        curriculum_view.current.content = build_curriculum_view()
        analytics_view.current.content = build_analytics_view()
        page.update()

    # Initial structure
    content = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            ref=main_column,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go(f"/organisations")),
                            ft.Text("Manage Playlist", size=24, weight=ft.FontWeight.BOLD)
                        ]),
                        ft.ElevatedButton("Save Changes", icon=ft.Icons.SAVE, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=on_save_curriculum)
                    ]
                ),
                ft.Tabs(
                    ref=tabs,
                    length=2,
                    selected_index=0,
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        controls=[
                            ft.TabBar(
                                tabs=[
                                    ft.Tab(label="Curriculum"),
                                    ft.Tab(label="Analytics")
                                ]
                            ),
                            ft.TabBarView(
                                expand=True,
                                controls=[
                                    ft.Container(padding=20, content=ft.ProgressRing(), ref=curriculum_view),
                                    ft.Container(padding=20, content=ft.ProgressRing(), ref=analytics_view)
                                ]
                            )
                        ]
                    )
                )
            ]
        )
    )

    # Fire and forget load
    asyncio.create_task(refresh_view())
    
    return ft.View(
        route=f"/playlists/{playlist_id}/build",
        controls=[ft.SafeArea(expand=True, content=content)]
    )