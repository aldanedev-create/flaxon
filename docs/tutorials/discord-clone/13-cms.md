# Lesson 13: Flaxon CMS for announcements

CMS is the editorial side of the staff console. `app.py` registers one content
type — an "announcement" with a title, a rich-text body, a pinned flag, and a
publish status:

```python
cms.register(ContentType(
    name="announcement",
    label="Announcement", label_plural="Announcements",
    fields=[
        CMSField("title", "Title", required=True),
        CMSField("body", "Body", type="richtext", required=True),
        CMSField("pinned", "Pin to top", type="boolean"),
        CMSField("status", "Status", type="select", choices=["draft", "published"]),
    ],
    list_display=["title", "pinned", "status", "updated_at"],
    search_fields=["title", "body"],
))
```

Announcements are authored at `/admin/cms/` and the SPA renders pinned,
published ones in its shell. Because the content type is registered on
`app.cms`, the model and admin UI are generated for you. Seeding a welcome
announcement is a few lines in `seed.py`:

```python
content_type = app.cms.content_types["announcement"]
content_type.create({"title": "Welcome to Flaxon HQ",
                     "body": "...", "pinned": True, "status": "published"})
app.cms._save(content_type)
```

**Checkpoint:** open `/admin/cms/`, create an announcement, publish it, and
confirm it appears in the app shell. Confirm a draft does not appear to users.
The registration itself is asserted in `tests/test_admin_cms.py`.
