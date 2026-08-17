import flet as ft
from src.components.completed_card import get_completed_card
from src.components.course_card import get_course_card
from src.components.playlist_card import get_playlist_card
from src.components.enrolled_card import get_enrolled_card
from src.components.org_course_card import get_org_course_card
from src.components.bottom_appbar import get_bottom_appbar
from src.requests.Courses import get_courses
from src.requests.enrollments import get_enrollments, enrol_user
from src.requests.playlists import get_all_playlists
from datetime import datetime

# Section keys/order for the hamburger drawer navigation.
# Landing section is "enrolled" (was previously the "Ongoing Courses" tab).
SECTION_ENROLLED = 0
SECTION_AVAILABLE = 1
SECTION_PLAYLISTS = 2
SECTION_COMPLETED = 3
SECTION_ORG = 4

async def courses_view(page: ft.Page):
    course_cards = []
    enroll_cards = []
    completed_cards = []
    playlist_cards = []
    org_cards = []
    
    # ── Filter States ──────────────────────────────────────────────────────────
    all_available_courses = []
    current_search_query = ""
    current_category_filter = None
    current_instructor_filter = None
    current_org_filter = None


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
          
    def build_course_card(course):
        course_name = course.get("name", "Untitled Course")
        image_url = course.get("image_url", None)
        course_id = course.get("id")
        first_name = course.get("admin", {}).get("first_name","Unknown")
        last_name = course.get("admin", {}).get("last_name","Instructor")
        full_name = f'{first_name} {last_name}'.strip()
        category = course.get("category",{}).get("name")
        created_at = course.get("created_at","")
        if created_at:
            created_at = datetime.fromisoformat(created_at).strftime("%d/%m/%Y")
        card = get_course_card(
            course_name, category, full_name, image_url, created_at,
            on_view_click=lambda e, c_id=course_id: page.go(f"/courses/{c_id}")
        )
        card.col = {"xs": 12, "sm": 6}
        return card

    def filter_courses(e=None):
        nonlocal current_search_query
        if e and getattr(e.control, "value", None) is not None:
            current_search_query = e.control.value.lower()
        elif 'search_tf_input' in locals() or 'search_tf_input' in globals() or hasattr(page, 'session'):
            # Fallback to reading the input value directly when filter changes
            # (handled by checking if search_tf_input is defined and initialized)
            try:
                current_search_query = search_tf_input.value.lower() if search_tf_input.value else ""
            except NameError:
                current_search_query = ""
            
        course_cards.clear()
        for course in all_available_courses:
            # 1. Search Query
            c_name = course.get("name", "").lower()
            if current_search_query and current_search_query not in c_name:
                continue
                
            # 2. Category
            c_cat = course.get("category", {}).get("name")
            if current_category_filter and c_cat != current_category_filter:
                continue
                
            # 3. Instructor
            c_first = course.get("admin", {}).get("first_name", "")
            c_last = course.get("admin", {}).get("last_name", "")
            c_instructor = f"{c_first} {c_last}".strip()
            if current_instructor_filter and c_instructor != current_instructor_filter:
                continue
                
            # 4. Org
            c_org = course.get("organisation", {}).get("name")
            if current_org_filter and c_org != current_org_filter:
                continue
                
            course_cards.append(build_course_card(course))
            
        if course_cards:
            course_container.content.controls = course_cards
        else:
            course_container.content.controls = [
                ft.Container(
                    padding=40,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=50, color=ft.Colors.ON_SURFACE),
                            ft.Text(
                                "No courses found for this filter.",
                                size=16,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                weight=ft.FontWeight.W_500,
                                text_align=ft.TextAlign.CENTER
                            )
                        ]
                    )
                )
            ]
        page.update()
        
        async def animate_cards():
            import asyncio
            await asyncio.sleep(0.02)
            if course_cards:
                for card in course_cards:
                    card.opacity = 1
                    card.offset = ft.Offset(0, 0)
                page.update()
                
        page.run_task(animate_cards)

    search_tf_input = ft.TextField(
        hint_text="Search courses or categories...",
        border=ft.InputBorder.NONE,
        on_change=filter_courses,
        on_submit=filter_courses,
        expand=True,
        content_padding=0,
    )
    
    def on_clear_search(e):
        search_tf_input.value = ""
        filter_courses()

    # 2. The UI Control (Search Bar - Refactored for perfect alignment)
    search_tf = ft.Container(
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=30,
        padding=ft.Padding(16, 4, 8, 4),
        expand=True,
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.SEARCH_ROUNDED, color=ft.Colors.ON_SURFACE_VARIANT, size=20),
                search_tf_input,
                ft.IconButton(icon=ft.Icons.CLEAR_ROUNDED, on_click=on_clear_search, icon_color=ft.Colors.ON_SURFACE_VARIANT, icon_size=20),
            ]
        )
    )
    
    # 3. Filter Bottom Sheets
    def build_filter_sheet(title, options, active_val, on_select):
        sheet = None
        
        def handle_select(e):
            on_select(e.control.value)
            if sheet:
                sheet.open = False
            page.update()
            filter_courses()
            
        def handle_reset(e):
            on_select(None)
            if sheet:
                sheet.open = False
            page.update()
            filter_courses()
            
        rg = ft.RadioGroup(
            value=active_val,
            on_change=handle_select,
            content=ft.Column(
                [ft.Radio(value=opt, label=opt) for opt in options],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )
        )
        
        sheet = ft.BottomSheet(
            ft.Container(
                padding=20,
                bgcolor=ft.Colors.SURFACE,
                border_radius=ft.BorderRadius.only(top_left=16, top_right=16),
                height=400,
                content=ft.Column([
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Container(content=rg, expand=True),
                    ft.Divider(),
                    ft.TextButton("Reset Filter", icon=ft.Icons.REFRESH, on_click=handle_reset)
                ])
            )
        )
        return sheet

    # Filter Chip UI Builder
    def create_filter_chip(label_text, on_click):
        return ft.Container(
            content=ft.Row([
                ft.Text(label_text, size=12, weight=ft.FontWeight.W_500),
                ft.Icon(ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=16)
            ], spacing=4),
            padding=ft.Padding(12, 6, 8, 6),
            border_radius=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            on_click=on_click,
            ink=True
        )

    def open_category_filter():
        cats = sorted(list(set(c.get("category", {}).get("name") for c in all_available_courses if c.get("category", {}).get("name"))))
        sheet = build_filter_sheet("Filter by Category", cats, current_category_filter, set_category_filter)
        page.show_dialog(sheet)
        
    def set_category_filter(val):
        nonlocal current_category_filter
        current_category_filter = val
        cat_chip.content.controls[0].value = f"Category: {val}" if val else "Category"
        cat_chip.bgcolor = ft.Colors.PRIMARY_CONTAINER if val else ft.Colors.SURFACE_CONTAINER_HIGHEST
        page.update()

    def open_instructor_filter():
        insts = sorted(list(set(f"{c.get('admin', {}).get('first_name', '')} {c.get('admin', {}).get('last_name', '')}".strip() for c in all_available_courses)))
        insts = [i for i in insts if i]
        sheet = build_filter_sheet("Filter by Instructor", insts, current_instructor_filter, set_instructor_filter)
        page.show_dialog(sheet)
        
    def set_instructor_filter(val):
        nonlocal current_instructor_filter
        current_instructor_filter = val
        inst_chip.content.controls[0].value = f"Instructor: {val}" if val else "Instructor"
        inst_chip.bgcolor = ft.Colors.PRIMARY_CONTAINER if val else ft.Colors.SURFACE_CONTAINER_HIGHEST
        page.update()

    def open_org_filter():
        orgs = sorted(list(set(c.get("organisation", {}).get("name") for c in all_available_courses if c.get("organisation", {}).get("name"))))
        sheet = build_filter_sheet("Filter by Organisation", orgs, current_org_filter, set_org_filter)
        page.show_dialog(sheet)
        
    def set_org_filter(val):
        nonlocal current_org_filter
        current_org_filter = val
        org_chip.content.controls[0].value = f"Org: {val}" if val else "Organisation"
        org_chip.bgcolor = ft.Colors.PRIMARY_CONTAINER if val else ft.Colors.SURFACE_CONTAINER_HIGHEST
        page.update()

    cat_chip = create_filter_chip("Category", lambda e: open_category_filter())
    inst_chip = create_filter_chip("Instructor", lambda e: open_instructor_filter())
    org_chip = create_filter_chip("Organisation", lambda e: open_org_filter())
    
    filter_row = ft.Row([cat_chip, inst_chip, org_chip], scroll=ft.ScrollMode.AUTO, spacing=8)
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
    playlist_container=ft.Container(
                        content=ft.ResponsiveRow(
                            spacing=20,
                            run_spacing=20,
                            controls=playlist_cards,
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
                # A: STATIC SEARCH & FILTER SECTION
                ft.Container(
                    content=ft.Column([
                        ft.Row([search_tf]),
                        filter_row
                    ], spacing=12),
                    padding=ft.Padding.only(bottom=10)
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

    playlists_section = ft.Container(
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                [ft.ProgressRing(color=ft.Colors.PRIMARY), ft.Text(" Fetching playlists...", color=ft.Colors.ON_SURFACE)],
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

    org_section = ft.Container(
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.ListView(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                [ft.ProgressRing(color=ft.Colors.PRIMARY), ft.Text(" Fetching organisation courses...", color=ft.Colors.ON_SURFACE)],
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
        SECTION_ORG: org_section,
    }

    SECTION_TITLES = {
        SECTION_ENROLLED: "My Courses",
        SECTION_AVAILABLE: "Available Courses",
        SECTION_PLAYLISTS: "Playlists",
        SECTION_COMPLETED: "Completed Courses",
        SECTION_ORG: "Organisation",
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
                icon=ft.Icon(ft.Icons.LIBRARY_BOOKS_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.LIBRARY_BOOKS_ROUNDED, color=ft.Colors.WHITE),
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
                label=ft.Text("Organisation", ref=drawer_label_refs[SECTION_ORG], color=ft.Colors.ON_SURFACE),
                icon=ft.Icon(ft.Icons.BUSINESS_OUTLINED, color=ft.Colors.ON_SURFACE),
                selected_icon=ft.Icon(ft.Icons.BUSINESS_ROUNDED, color=ft.Colors.WHITE),
                visible=False,
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
        playlists = await get_all_playlists(token)

        all_available_courses.clear()
        for course in course_list:
            course_id = course.get("id")
            if course_id not in enrolled_ids and course_id not in completed_ids:
                all_available_courses.append(course)
        
        # Run the filter to initially populate course_cards
        filter_courses()
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
                    rating = course.get("rating", 0.0)
                    card = get_enrolled_card(page,course_id,course_name,category,full_name,image_url,progress,rating)
                    card.on_click = lambda e, c_id=course_id,c_name=course_name: page.go(f"/courses/{c_id}/view")
                    card.col = {"xs": 12, "sm": 6}
                    enroll_cards.append(card)
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
        else:
            print(completed_list)
            completed_list.clear()

        if isinstance(playlists, list):
            for playlist in playlists:
                p_name = playlist.get("name", "Untitled")
                p_img = playlist.get("image_url", "")
                p_id = playlist.get("id")
                org = playlist.get("Organisation", "Organisation")
                created_at = playlist.get("created_at", "")
                if created_at:
                    created_at = datetime.fromisoformat(created_at).strftime("%d/%m/%Y")
                card = get_playlist_card(p_name, org, p_img, created_at, on_enroll_click=lambda e, cid=p_id: page.go(f"/playlists/{cid}"))
                card.on_click = lambda e, pid=p_id: page.go(f"/playlists/{pid}")
                card.col = {"xs": 12, "sm": 6}
                playlist_cards.append(card)

        # Rebuild each real section's content in place (mirrors the old
        # TabBarView panes exactly, just re-housed under the drawer nav).
        available_section.content = ft.Column(
            expand=True,
            controls=[
                # A: STATIC SEARCH & FILTER SECTION
                ft.Container(
                    content=ft.Column([
                        ft.Row([search_tf]),
                        filter_row
                    ], spacing=12),
                    padding=ft.Padding.only(bottom=10)
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

        playlists_section.content = ft.Column(
            controls=[
                ft.ListView(
                    expand=True,
                    controls=[
                        playlist_container if playlist_cards else ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "There are no playlists available",
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

        org_list = await get_courses(token, {"is_public": "organisation"})
        if isinstance(org_list, list) and len(org_list) > 0:
            nav_drawer.controls[5].visible = True
            for course in org_list:
                course_name = course.get("name", "Untitled Course")
                image_url = course.get("image_url", "")
                course_id = course.get("id")
                if course_id not in enrolled_ids and course_id not in completed_ids:
                    category = course.get("category",{}).get("name")
                    org_name = course.get("organisation", {}).get("name", "Organisation")
                    created_at = course.get("created_at","")
                    if created_at and "T" in created_at:
                        created_at = datetime.fromisoformat(created_at).strftime("%d/%m/%Y")
                    
                    card = get_org_course_card(
                        course_name, category, org_name, image_url, created_at, 
                        on_view_click=lambda e, cid=course_id: page.go(f"/courses/{cid}")
                    )
                    card.col = {"xs": 12, "sm": 6}
                    org_cards.append(card)
        else:
            nav_drawer.controls[5].visible = False
            
        org_container = ft.ResponsiveRow(spacing=20)
        org_container.controls = org_cards
        
        org_section.content = ft.Column(
            controls=[
                ft.ListView(
                    expand=True,
                    controls=[
                        org_container if org_cards else ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "No organisation courses available",
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
        
        async def animate_all_cards():
            import asyncio
            await asyncio.sleep(0.02)
            for card_list in [enroll_cards, completed_cards, playlist_cards, org_cards]:
                if card_list:
                    for card in card_list:
                        card.opacity = 1
                        card.offset = ft.Offset(0, 0)
            page.update()
            
        page.run_task(animate_all_cards)
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