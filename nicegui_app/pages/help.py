"""Help documentation page with searchable chapters."""
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode
from src.services.help_service import HelpService


def help_page():
    """Help page content."""
    apply_dark_mode()

    # Get user role for filtering help content
    user_role = app.storage.general.get('user', {}).get('role', 'employee')

    # State for current view
    current_view = {'chapter': None, 'article': None}
    search_results = {'items': []}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header using shared component (no help button on help page itself)
        page_header(title='HELP CENTER', show_back=False)

        # Search bar (debounce to reduce processing)
        search_input = ui.input(placeholder='Search help articles...').classes('w-full mb-4').props('outlined dense clearable debounce="300"')

        # Content container
        content_container = ui.column().classes('w-full')

        def show_chapters():
            """Show all chapters (home view)."""
            current_view['chapter'] = None
            current_view['article'] = None
            content_container.clear()
            with content_container:
                chapters = HelpService.get_all_chapters(user_role)
                # Use CSS grid for consistent card sizing
                with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;'):
                    for chapter in chapters:
                        with ui.card().classes('cursor-pointer hover:shadow-lg transition-shadow h-full').style('border-left: 4px solid #C9A227;').on('click', lambda c=chapter['id']: show_chapter(c)):
                            with ui.card_section().classes('h-full'):
                                with ui.row().classes('items-center gap-3 mb-3'):
                                    ui.icon(chapter['icon'], size='2rem').style('color: #C9A227;')
                                    ui.label(chapter['title']).classes('text-lg font-semibold')
                                ui.label(f"{chapter['article_count']} articles").classes('text-sm opacity-70 mb-2')
                                for article in chapter['articles'][:3]:
                                    ui.label(f"• {article['title']}").classes('text-sm truncate')
                                if len(chapter['articles']) > 3:
                                    ui.label(f"  + {len(chapter['articles']) - 3} more...").classes('text-xs opacity-50')

        def show_chapter(chapter_id):
            """Show articles in a chapter."""
            current_view['chapter'] = chapter_id
            current_view['article'] = None
            content_container.clear()
            with content_container:
                chapter = HelpService.get_chapter(chapter_id, user_role)
                if not chapter:
                    ui.label('Chapter not found')
                    return

                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').style('color: #C9A227; cursor: pointer;').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(chapter['title']).classes('font-semibold')

                # Articles list
                with ui.card().classes('w-full'):
                    for article in chapter['articles']:
                        with ui.row().classes('w-full p-4 border-b last:border-0 items-center cursor-pointer').style('transition: background-color 0.2s;').on('click', lambda a=article['id'], c=chapter_id: show_article(c, a)):
                            ui.icon('article').style('color: #C9A227;').classes('mr-3')
                            ui.label(article['title']).classes('text-lg')
                            ui.space()
                            ui.icon('chevron_right').classes('opacity-50')

        def show_article(chapter_id, article_id):
            """Show a single article."""
            current_view['chapter'] = chapter_id
            current_view['article'] = article_id
            content_container.clear()
            with content_container:
                article = HelpService.get_article(chapter_id, article_id, user_role)
                if not article:
                    ui.label('Article not found')
                    return

                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').style('color: #C9A227; cursor: pointer;').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(article['chapter_title']).style('color: #C9A227; cursor: pointer;').on('click', lambda c=chapter_id: show_chapter(c))
                    ui.label('/').classes('opacity-50')
                    ui.label(article['title']).classes('font-semibold')

                # Article content
                with ui.card().classes('w-full p-6'):
                    ui.markdown(article['content']).classes('prose max-w-none prose-headings:text-[#C9A227]')

        def do_search(e):
            """Perform search and show results."""
            query = e.value if hasattr(e, 'value') else search_input.value
            if not query or len(query) < 2:
                show_chapters()
                return

            results = HelpService.search(query, user_role)
            content_container.clear()
            with content_container:
                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').style('color: #C9A227; cursor: pointer;').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(f'Search: "{query}"').classes('font-semibold')

                if not results:
                    with ui.card().classes('w-full p-8 text-center'):
                        ui.icon('search_off', size='3rem').style('color: #C9A227; opacity: 0.3;').classes('mb-2')
                        ui.label(f'No results found for "{query}"').classes('text-lg opacity-60')
                else:
                    ui.label(f'{len(results)} result(s) found').classes('text-sm opacity-70 mb-2')
                    with ui.card().classes('w-full'):
                        for result in results:
                            with ui.row().classes('w-full p-4 border-b last:border-0 cursor-pointer').style('transition: background-color 0.2s;').on('click', lambda r=result: show_article(r['chapter_id'], r['article_id'])):
                                with ui.column().classes('flex-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(result['article_title']).classes('font-semibold')
                                        ui.badge(result['chapter_title']).style('background-color: #C9A227 !important;').classes('text-xs')
                                    if result['snippet']:
                                        ui.label(result['snippet']).classes('text-sm opacity-70 mt-1')

        search_input.on('keydown.enter', do_search)

        # Initial view
        show_chapters()

        # Back button - uses browser history for proper navigation
        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6').style('border-color: #C9A227 !important; color: #C9A227 !important;')
