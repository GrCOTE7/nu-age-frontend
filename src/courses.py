import flet as ft
from src.components.completed_card import get_completed_card
from src.components.course_card import get_course_card
from src.components.enrolled_card import get_enrolled_card
from src.components.bottom_appbar import get_bottom_appbar
from src.requests.Courses import get_courses
from src.requests.enrollments import get_enrollments, enrol_user
from datetime import datetime

# Section keys/order for the hamburger drawer navigation.
# Landing section is "enrolled" (was previously the "Ongoing Courses" tab).
SECTION_ENROLLED = 0
SECTION_AVAILABLE = 1
SECTION_PLAYLISTS = 2
SECTION_COMPLETED = 3
SECTION_SAVED = 4

async def courses_view(page: ft.Page):
    course_cards = []
    enroll_cards = []
    completed_cards = []

    async def clear_search(e):
        if e.control.value == "":
            await handle_change(e)
        else:
            pass
        
    async def handle_enrol_click(e,course_id:str):
        token = await page.shared_preferences.get("auth_token")
        if e.control.disabled:
            return
        
        e.control.disabled = True
        # Using ON_PRIMARY for the ring inside the button
        e.control.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.ON_PRIMARY)
        is_enrolling = True
        page.update()
        
        try:
            if is_enrolling:
                status, data = await enrol_user(token, course_id, None)
            else:
                pass # Unenroll logic here
            
            if status == 200:
                e.control.content= ft.Text("Fetching Course Contents...", color=ft.Colors.WHITE)
                page.update()
                page.go(f"/courses/{course_id}/view")
            else:
                e.control.disabled = False
                e.control.content = ft.Text("Enroll") 
                page.update()
        except Exception:
            e.control.disabled = False
            page.update()
            e.control.content = ft.Text("Enroll")
            page.update()
          
    async def handle_change(e):
        new_token = await page.shared_preferences.get("auth_token")
        course_list = await get_courses(new_token, params={"name": e.control.value, "is_public": True})
        if isinstance(course_list, list): 
            course_cards.clear()
            for course in course_list:
                course_name = course.get("name", "Untitled Course")
                first_name = course.get("admin", {}).get("first_name","Unknown")
                last_name = course.get("admin", {}).get("last_name","Instructor")
                full_name = f'{first_name} {last_name}'
                category = course.get("category",{}).get("name")
                image_url = course.get("image_url",None)
                course_id = course.get("id")
                created_at = course.get("created_at","")
                created_at = datetime.fromisoformat(created_at)
                # 2. Format to Day/Month/Year
                created_at = created_at.strftime("%d/%m/%Y")
                card = get_course_card(course_name,category,full_name, image_url,created_at)
                card.on_click = lambda e, c_id=course_id: page.go(f"/courses/{c_id}")
                card.col = {"xs": 12, "sm": 6}
                course_cards.append(card)
            course_container.content.controls = course_cards if course_cards else ft.Container(
                        padding=40,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=50, color=ft.Colors.ON_SURFACE),
                                ft.Text(
                                    "Try a different Search",
                                    size=16,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_500,
                                    text_align=ft.TextAlign.CENTER
                                )]))
            page.update()
            if isinstance(course_container.content.controls, list):
                for card in course_container.content.controls :
                    card.offset = ft.Offset(0, 0) # Move to original position
                    card.opacity = 1
        else:
            pass
        page.update()

    # 2. The UI Control
    
    search_anchor = ft.SearchBar(
        bar_bgcolor=ft.Colors.ON_PRIMARY, # Themed equivalent of White
        bar_hint_text="Search courses or categories...",
        bar_leading=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.PRIMARY), # Themed equivalent of #009787
        
        # Style the dropdown view to match Nu-age
        view_bgcolor=ft.Colors.SURFACE,
        view_hint_text="Type to find a course...",
        
        # Behavior
        on_submit=handle_change,
        on_change=clear_search,
    
        # UI Polish
        bar_elevation=1,
        bar_padding=ft.Padding(left=15, right=15, top=0, bottom=0),
        expand=True
    )
    App_bar = get_bottom_appbar(page)

    # Section title shown in the top app bar, updates as the user navigates the drawer.
    section_title_text = ft.Text(
        value="My Courses",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.ON_PRIMARY,
    )

    course_container=ft.Container(
                        content=ft.ResponsiveRow(
                            spacing=20,          # Horizontal space between cards
                            run_spacing=20,
                            controls=course_cards, # Blank for now
                        ),
                        padding=20)
    enroll_container=ft.Container(
                        content=ft.ResponsiveRow(
                            spacing=20,          # Horizontal space between cards
                            run_spacing=20,
                            controls=enroll_cards, # Blank for now
                        ),
                        padding=20)
    completed_container=ft.Container(
                        content=ft.ResponsiveRow(
                            spacing=20,          # Horizontal space between cards
                            run_spacing=20,
                            controls=completed_cards, # Blank for now
                        ),
                        padding=20)
    # -------------------------------------------------------------------
    # Section content areas (one per hamburger-drawer destination).
    # These replace the old TabBarView panes 1:1 in content/behavior;
    # only the navigation chrome around them has changed.
    # -------------------------------------------------------------------

    available_section = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            expand=True,
            controls=[
                # A: STATIC SEARCH SECTION
                ft.Container(
                    content=ft.Row([search_anchor]),
                    # No expand=True here, we want it to stay at its natural height
                ),

                # B: SCROLLABLE SECTION
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        # Check if we actually have cards to show
                        ft.Container(
                            content=ft.Row(
                                [ft.ProgressRing(color=ft.Colors.PRIMARY), ft.Text(" Getting available courses...", color=ft.Colors.ON_SURFACE)],
                                alignment=ft.MainAxisAlignment.CENTER
                            ),
                            height=200,
                        )
                    ],
                )
            ]
        )
    )

    enrolled_section = ft.Container(
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER, # Center loading ring
            controls=[
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                [ft.ProgressRing(color=ft.Colors.PRIMARY), ft.Text(" Fetching your courses...", color=ft.Colors.ON_SURFACE)],
                                alignment=ft.MainAxisAlignment.CENTER
                            ),
                            height=200,
                        )
                    ],
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        ),
        padding=20,
        expand=True,
    )

    completed_section = ft.Container(
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER, # Center loading ring
            controls=[
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                [ft.ProgressRing(color=ft.Colors.PRIMARY), ft.Text(" Getting your completed courses...", color=ft.Colors.ON_SURFACE)],
                                alignment=ft.MainAxisAlignment.CENTER
                            ),
                            height=200,
                        )
                    ],
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        ),
        padding=20,
        expand=True,
    )

    # --- Placeholder sections (mock content, to be built out later) ---

    def _placeholder_section(icon, title, subtitle):
        return ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(height=12),
                    ft.Text(
                        title,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        subtitle,
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=16),
                    ft.Container(
                        padding=ft.Padding(left=14, right=14, top=6, bottom=6),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border_radius=20,
                        content=ft.Text(
                            "Coming soon",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ),
                ],
            ),
        )

    playlists_section = _placeholder_section(
        ft.Icons.PLAYLIST_PLAY_ROUNDED,
        "Playlists",
        "Curated playlists of courses and lessons will show up here.",
    )

    saved_section = _placeholder_section(
        ft.Icons.DOWNLOAD_FOR_OFFLINE_ROUNDED,
        "Saved / Offline Courses",
        "Courses you save for offline viewing will show up here.",
    )

    # Container that holds whichever section is currently active.
    # Its `.content` gets swapped whenever the drawer selection changes,
    # replacing the old TabBarView-driven switching.
    section_body = ft.Container(
        expand=True,
        content=enrolled_section,  # Landing page: Enrolled Courses
    )

    SECTION_CONTENT = {
        SECTION_ENROLLED: enrolled_section,
        SECTION_AVAILABLE: available_section,
        SECTION_PLAYLISTS: playlists_section,
        SECTION_COMPLETED: completed_section,
        SECTION_SAVED: saved_section,
    }

    SECTION_TITLES = {
        SECTION_ENROLLED: "My Courses",
        SECTION_AVAILABLE: "Available Courses",
        SECTION_PLAYLISTS: "Playlists",
        SECTION_COMPLETED: "Completed Courses",
        SECTION_SAVED: "Saved / Offline",
    }

    def update_drawer_label_colors(selected_index: int):
        # Selected destination's label goes white (readable against the
        # PRIMARY indicator_color pill); everything else stays ON_SURFACE.
        for i, label_ref in enumerate(drawer_label_refs):
            label_ref.current.color = ft.Colors.WHITE if i == selected_index else ft.Colors.ON_SURFACE

    def show_section(index: int):
        section_body.content = SECTION_CONTENT[index]
        section_title_text.value = SECTION_TITLES[index]
        nav_drawer.selected_index = index
        update_drawer_label_colors(index)
        page.update()

    async def handle_drawer_change(e):
        # NOTE: page.close() (not nav_drawer.open = False + .update()) is the
        # reliable way to dismiss a drawer that's attached via View.drawer.
        # Flipping .open and calling .update()/nav_drawer.update() is a known
        # no-op in this scenario (flet-dev/flet#5163).
        await page.close_drawer()
        show_section(e.control.selected_index)

    # Refs to each destination's label Text, ordered by section index, so we
    # can flip the active one to white (readable on the PRIMARY indicator
    # pill) while the rest stay ON_SURFACE.
    drawer_label_refs = [ft.Ref[ft.Text]() for _ in range(5)]

    nav_drawer = ft.NavigationDrawer(
        tile_padding=ft.Padding(top=10),
        selected_index=SECTION_ENROLLED,
        on_change=handle_drawer_change,
        #on_dismiss=lambda e: page.close(nav_drawer),  # keeps drawer.open state in sync on swipe/tap-outside dismiss
        bgcolor=ft.Colors.SURFACE,
        indicator_color=ft.Colors.PRIMARY,
        indicator_shape=ft.RoundedRectangleBorder(radius=6),  # squarer selection pill instead of default stadium shape
        controls=[
            ft.Container(
                height=60,
                bgcolor= ft.Colors.PRIMARY,
                padding=ft.Padding(left=16, right=16, top=15, bottom=16),
                content=ft.Text(
                    "What are we learning today?",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_PRIMARY,
                ),
            ),
            ft.NavigationDrawerDestination(
                label=ft.Text("Enrolled Courses", ref=drawer_label_refs[SECTION_ENROLLED], color=ft.Colors.WHITE),
                icon=ft.Icon(ft.Icons.SCHOOL_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.SCHOOL_ROUNDED, color=ft.Colors.WHITE),
            ),
            ft.NavigationDrawerDestination(
                label=ft.Text("Available Courses", ref=drawer_label_refs[SECTION_AVAILABLE], color=ft.Colors.ON_SURFACE),
                icon=ft.Icon(ft.Icons.EXPLORE_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.EXPLORE_ROUNDED, color=ft.Colors.WHITE),
            ),
            ft.NavigationDrawerDestination(
                label=ft.Text("Playlists", ref=drawer_label_refs[SECTION_PLAYLISTS], color=ft.Colors.ON_SURFACE),
                icon=ft.Icon(ft.Icons.PLAYLIST_PLAY_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.PLAYLIST_PLAY_ROUNDED, color=ft.Colors.WHITE),
            ),
            ft.NavigationDrawerDestination(
                label=ft.Text("Completed Courses", ref=drawer_label_refs[SECTION_COMPLETED], color=ft.Colors.ON_SURFACE),
                icon=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ft.Colors.WHITE),
            ),
            ft.NavigationDrawerDestination(
                label=ft.Text("Saved / Offline", ref=drawer_label_refs[SECTION_SAVED], color=ft.Colors.ON_SURFACE),
                icon=ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_ROUNDED, color=ft.Colors.WHITE),
            ),
        ],
    )

    async def open_drawer(e):
        # page.open() is the current, reliable way to show overlay controls
        # (NavigationDrawer, BottomSheet, AlertDialog, etc). Setting
        # nav_drawer.open = True and calling page.update() is the old pattern
        # and is known to silently no-op when the drawer is attached via
        # View.drawer instead of Page.drawer (flet-dev/flet#5163) - which is
        # exactly this setup, hence the tap doing nothing with no error.
        await page.show_drawer()

    header_container = ft.Container(
        bgcolor=ft.Colors.PRIMARY, # Themed equivalent of #009787
        height=68,
        border_radius=ft.BorderRadius.only(bottom_left=12, bottom_right=12),
        padding=ft.Padding.only(top=10, left=10, right=25, bottom=20),
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.PRIMARY, ft.Colors.SECONDARY],
        ),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.MENU_ROUNDED,
                    icon_color=ft.Colors.ON_PRIMARY,
                    tooltip="Menu",
                    on_click=open_drawer,
                ),
                section_title_text,
            ],
        ),
    )

    async def populate_tabs():
        token = await page.shared_preferences.get("auth_token")
        course_list = await get_courses(token, {"is_public": True})
        enrolled_list = await get_enrollments(token,None)
        completed_list = await get_courses(token, {"progress": 100})
        enrolled_ids = {course.get("id") for course in enrolled_list}
        completed_ids = {course.get("id") for course in completed_list}

        for course in course_list:
            course_name = course.get("name", "Untitled Course")
            image_url = course.get("image_url", "")
            course_id = course.get("id")
            if course_id not in enrolled_ids and course_id not in completed_ids:
                first_name = course.get("admin", {}).get("first_name","Unknown")
                last_name = course.get("admin", {}).get("last_name","Instructor")
                full_name = f'{first_name} {last_name}'
                category = course.get("category",{}).get("name")
                created_at = course.get("created_at","")
                created_at = datetime.fromisoformat(created_at)
                # 2. Format to Day/Month/Year
                created_at = created_at.strftime("%d/%m/%Y")
                card = get_course_card(course_name,category,full_name,image_url,created_at,on_enroll_click=lambda e, c_id=course_id: e.page.run_task(handle_enrol_click, e, c_id))
                card.on_click = lambda e, c_id=course_id, c_name=course_name: page.go(f"/courses/{c_id}/{c_name}")
                card.col = {"xs": 12, "sm": 6}
                course_cards.append(card)
                card.opacity = 1
                card.offset = ft.Offset(0, 0)
        if isinstance(enrolled_list, list):  
            for course in enrolled_list:
                course_name = course.get("name", "Untitled Course")
                image_url = course.get("image_url", "")
                course_id = course.get("id")
                if course_id not in completed_ids:
                    progress = course.get("progress", 0.0)
                    first_name = course.get("admin", {}).get("first_name","Unknown")
                    last_name = course.get("admin", {}).get("last_name","Instructor")
                    full_name = f'{first_name} {last_name}'
                    category = course.get("category",{}).get("name")
                    card = get_enrolled_card(course_name,category,full_name,image_url,progress)
                    card.on_click = lambda e, c_id=course_id,c_name=course_name: page.go(f"/courses/{c_id}/view")
                    card.col = {"xs": 12, "sm": 6}
                    enroll_cards.append(card)
                    card.opacity = 1
                    card.offset = ft.Offset(0, 0)
        else:
            enrolled_list.clear()
        if isinstance(completed_list, list):
            for course in completed_list:
                course_name = course.get("name", "Untitled Course")
                image_url = course.get("image_url", "")
                course_id = course.get("id")
                first_name = course.get("admin", {}).get("first_name","Unknown")
                last_name = course.get("admin", {}).get("last_name","Instructor")
                full_name = f'{first_name} {last_name}'
                category = course.get("category",{}).get("name")
                card = get_completed_card(course_name,course_id, on_review_click=lambda e, cid=course_id: page.go(f"/courses/{cid}/view"), on_stats_click=lambda e, cid=course_id: page.go(f"/courses/{cid}/stats"))
                card.col = {"xs": 12, "sm": 6}
                completed_cards.append(card)
                card.opacity = 1
                card.offset = ft.Offset(0, 0)
        else:
            print(completed_list)
            completed_list.clear()
        # Rebuild each real section's content in place (mirrors the old
        # TabBarView panes exactly, just re-housed under the drawer nav).
        available_section.content = ft.Column(
            expand=True,
            controls=[
                # A: STATIC SEARCH SECTION
                ft.Container(
                    content=ft.Row([search_anchor]),
                    # No expand=True here, we want it to stay at its natural height
                ),

                # B: SCROLLABLE SECTION
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        # Check if we actually have cards to show
                        course_container if course_cards else ft.Container(
                            padding=40,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=50, color=ft.Colors.ON_SURFACE),
                                    ft.Text(
                                        "No available courses found",
                                        size=16,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        weight=ft.FontWeight.W_500,
                                        text_align=ft.TextAlign.CENTER
                                    ),
                                ]
                            )
                        )
                    ],
                )
            ]
        )

        enrolled_section.content = ft.Column(
            controls=[
                ft.ListView(
                    expand=True, # THIS IS VITAL - it fills the remaining space
                    controls=[
                        enroll_container if enroll_cards else ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "You have no enrolled courses",
                                    size=16,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_500
                                )
                            ]
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        completed_section.content = ft.Column(
            controls=[
                ft.ListView(
                    expand=True, # THIS IS VITAL - it fills the remaining space
                    controls=[
                        completed_container if completed_cards else ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "You have no completed courses",
                                    size=16,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_500
                                )
                            ]
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        page.update()

    # 2. Return the View
    page.run_task(populate_tabs)
    return ft.View(
        route="/courses",
        bottom_appbar=App_bar,
        drawer=nav_drawer,
        # 1. Important: Ensure the view padding doesn't interfere
        padding=0, 
        bgcolor=ft.Colors.ON_PRIMARY,

        controls=[
            ft.SafeArea(
                # 2. This Column must fill the screen height
                expand=True, 
                content=ft.Column(
                    expand=True, # 3. Force this to be exactly the screen height
                    spacing=0,
                    controls=[
                        header_container,
                        # 4. Wrap the active section in a container that takes the REMAINING space
                        section_body,
                    ]
                )
            )
        ],
    )