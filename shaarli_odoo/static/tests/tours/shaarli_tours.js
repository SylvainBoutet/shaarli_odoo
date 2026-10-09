/** @odoo-module **/

import { registry } from "@web/core/registry";

// These tours rely on the data created by tests/test_tours.py.

registry.category("web_tour.tours").add("shaarli_public_tour", {
    test: true,
    url: "/bookmarks",
    steps: () => [
        {
            content: "The external link opens a new tab",
            trigger: "a.o_bookmark_external[href='https://tour.example.com'][target='_blank'][rel*='noopener']",
            isCheck: true,
        },
        {
            content: "Filter on the tour tag",
            trigger: ".tag-filter a:contains('tourtag')",
            run: "click",
        },
        {
            content: "The selected tag is highlighted",
            trigger: ".tag-filter a.active.btn-primary:contains('tourtag')",
            isCheck: true,
        },
        {
            content: "All is no longer highlighted",
            trigger: ".tag-filter a:not(.active):contains('All')",
            isCheck: true,
        },
        {
            content: "Open the detail page from the title",
            trigger: "a.o_bookmark_title:contains('Tour Public Bookmark')",
            run: "click",
        },
        {
            content: "The detail page shows the bookmark",
            trigger: "h1:contains('Tour Public Bookmark')",
            isCheck: true,
        },
        {
            content: "The favicon is a valid data URI",
            trigger: "img.o_bookmark_favicon[src='data:image/png;base64,aWNvbi1ieXRlcw==']",
            isCheck: true,
        },
        {
            content: "The tags of the bookmark are listed",
            trigger: "a.o_bookmark_detail_tag:contains('tourtag')",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("shaarli_backend_tour", {
    test: true,
    url: "/web#action=shaarli_odoo.action_bookmarks",
    steps: () => [
        {
            content: "Switch to the kanban view",
            trigger: "button.o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "Kanban: the domain is on its own line under the title",
            trigger: ".o_kanban_record:contains('Tour Private Bookmark') .o_kanban_record_subtitle.d-block:contains('tour.example.org')",
            isCheck: true,
        },
        {
            content: "Switch to the list view",
            trigger: "button.o_switch_view.o_list",
            run: "click",
        },
        {
            content: "The owner column shows the owner",
            trigger: ".o_data_row:contains('Tour Private Bookmark') td[name='user_id']:contains('Tour Owner')",
            isCheck: true,
        },
        {
            content: "Open the bookmark",
            trigger: ".o_data_row td[name='name']:contains('Tour Private Bookmark')",
            run: "click",
        },
        {
            content: "Archive the page",
            trigger: ".o_form_view .o_form_statusbar button[name='action_archive_page']",
            run: "click",
        },
        {
            content: "The form is reloaded with the archive",
            trigger: ".o_form_view .o_form_statusbar button[name='action_view_archive']",
            isCheck: true,
        },
        {
            content: "The archive button is hidden once archived",
            trigger: ".o_form_view .o_form_statusbar:not(:has(button[name='action_archive_page']))",
            isCheck: true,
        },
        {
            content: "The breadcrumb leads back to the list",
            trigger: ".o_breadcrumb .breadcrumb-item:contains('Bookmarks')",
            run: "click",
        },
        {
            content: "Back on the list",
            trigger: ".o_list_view .o_data_row:contains('Tour Private Bookmark')",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("shaarli_new_bookmark_tour", {
    test: true,
    url: "/web#action=shaarli_odoo.action_bookmarks&view_type=form",
    steps: () => [
        {
            content: "A new bookmark has no Open URL nor Archive Page button",
            trigger: ".o_form_view:has(.o_form_sheet):not(:has(button[name='action_open_url'])):not(:has(button[name='action_archive_page']))",
            isCheck: true,
        },
        {
            content: "Title",
            trigger: ".o_form_view div[name='name'] input",
            run: "text Tour New Bookmark",
        },
        {
            content: "URL",
            trigger: ".o_form_view div[name='url'] input",
            run: "text tour-new.example.com",
        },
        {
            content: "Save",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Once saved, the buttons are shown",
            trigger: ".o_form_view .o_form_statusbar button[name='action_open_url'] ~ button[name='action_archive_page']",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("shaarli_tags_tour", {
    test: true,
    url: "/web#action=shaarli_odoo.action_bookmark_tags",
    steps: () => [
        {
            content: "The color column has a readable label",
            trigger: ".o_list_view th[data-name='color']:contains('Color'):not(:contains('Index'))",
            isCheck: true,
        },
        {
            content: "The color is shown as a color",
            trigger: ".o_data_row:contains('tourtag') td[name='color'] .o_field_color_picker",
            isCheck: true,
        },
        {
            content: "The owner column shows the owner",
            trigger: ".o_data_row:contains('tourtag') td[name='user_id']:contains('Tour Owner')",
            isCheck: true,
        },
    ],
});
