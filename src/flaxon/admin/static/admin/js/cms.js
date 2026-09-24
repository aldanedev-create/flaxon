  const API_BASE = window.FLAXON_CMS_API_BASE || "__CMS_API_BASE__";
  const CSRF_TOKEN = window.FLAXON_CMS_CSRF_TOKEN || "__CMS_CSRF_TOKEN__";

    function csrfToken() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return (meta && meta.content) || window.FLAXON_CMS_CSRF_TOKEN || CSRF_TOKEN;
    }

    function cmsApp() {
      return {
        title: "__CMS_TITLE__",
        types: [],
        stats: {},
        view: "dashboard",
        currentType: null,
        error: null,
        loading: false,
        darkMode: localStorage.getItem("admin-dark-mode") !== "false",

        listItems: [],
        listMeta: { total: 0, page: 1, pages: 1, per_page: 20 },
        listQuery: { q: "" },
        selected: [],
        bulkAction: "",

        editingId: null,
        formData: {},
        resource: null,
        resourceItems: [],
        resourceDraft: {},
        dragMenuIndex: null,
        taxonomyName: "",
        taxonomyTerm: "",
        dirty: false,
        autosaveTimer: null,
        schedulerJobs: [],
        revisionCompare: null,
        mediaItems: [],
        mediaPickerField: null,
        workspaceSection: null,
        workspaceItems: [],
        workspaceStats: {},
        workspaceTitle: "CMS workspace",
        workspaceDescription: "Operational content workspace",
        workspaceLinks: [
          { name: "calendar", label: "Calendar", icon: "fa-calendar-days", description: "Scheduled publishing calendar" },
          { name: "board", label: "Board", icon: "fa-table-columns", description: "Editorial workflow board" },
          { name: "review", label: "Review", icon: "fa-clipboard-check", description: "Content awaiting review" },
          { name: "models", label: "Models", icon: "fa-cubes", description: "Content model registry" },
          { name: "media", label: "Media", icon: "fa-photo-film", description: "Reusable media library" },
          { name: "seo", label: "SEO", icon: "fa-magnifying-glass-chart", description: "Search metadata and index state" },
          { name: "comments", label: "Moderation", icon: "fa-comments", description: "Comment moderation queue" },
          { name: "menus", label: "Menus", icon: "fa-list", description: "Navigation hierarchy" },
          { name: "audit", label: "Audit", icon: "fa-shield-halved", description: "Content activity history" },
        ],

        async init() {
          this.applyTheme();
          await this.loadConfig();
          document.addEventListener("dragstart", (event) => {
            const item = event.target.closest?.('[draggable="true"]');
            if (!item) return;
            this.dragMenuIndex = Array.from(item.parentElement.children).indexOf(item);
          });
          document.addEventListener("dragover", (event) => {
            if (event.target.closest?.('[draggable="true"]')) event.preventDefault();
          });
          document.addEventListener("drop", (event) => {
            const item = event.target.closest?.('[draggable="true"]');
            if (!item) return;
            event.preventDefault();
            this.dropMenuItem(Array.from(item.parentElement.children).indexOf(item));
          });
          window.addEventListener("beforeunload", (event) => { if (this.view === "form" && this.dirty) { event.preventDefault(); event.returnValue = ""; } });
          window.addEventListener("hashchange", () => this.route());
          this.route();
        },

        toggleTheme() {
          this.darkMode = !this.darkMode;
          localStorage.setItem("admin-dark-mode", this.darkMode);
          this.applyTheme();
        },
        applyTheme() {
          document.documentElement.classList.toggle("dark", this.darkMode);
          document.documentElement.classList.toggle("light", !this.darkMode);
          document.documentElement.dataset.theme = this.darkMode ? "dark" : "light";
          document.body.classList.toggle("theme-dark", this.darkMode);
          document.body.classList.toggle("theme-light", !this.darkMode);
          document.body.dataset.theme = this.darkMode ? "dark" : "light";
          document.documentElement.style.colorScheme = this.darkMode ? "dark" : "light";
        },

        async api(path, options = {}) {
            this.loading = true;
          try {
            const request = () => fetch(API_BASE + path, {
              ...options,
              headers: {
                ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
                ...(csrfToken() ? { "X-CSRF-Token": csrfToken() } : {}),
                ...(options.headers || {}),
              },
            });
            let res = await request();
            if (res.status >= 500) { await new Promise(resolve => setTimeout(resolve, 250)); res = await request(); }
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
              const detail = data.error?.message || data.error?.detail || data.message || data.error;
              this.error = detail || `Request failed (${res.status})`;
              return null;
            }
            return data;
          } catch (e) {
            this.error = "Network error: " + e.message;
            return null;
          } finally {
            this.loading = false;
          }
        },

        async loadConfig() {
          const config = await this.api("/config");
          if (config) {
            this.title = config.title;
            this.types = config.types;
          }
          const stats = await this.api("/stats");
          if (stats) this.stats = stats;
          const scheduler = await this.api("/scheduler/jobs");
          if (scheduler) this.schedulerJobs = scheduler.items || [];
        },

        route() {
          const hash = window.location.hash.replace(/^#\/?/, "");
          const parts = hash.split("/").filter(Boolean);
          if (parts.length === 0) {
            this.view = "dashboard";
            this.currentType = null;
          } else if (parts[0] === "workspace" && parts[1]) {
            this.openWorkspace(parts[1], false);
          } else if (parts.length === 1 && this.workspaceLinks.some((item) => item.name === parts[0])) {
            this.openWorkspace(parts[0], false);
          } else if (parts.length === 1) {
            this.openList(parts[0], false);
          } else if (parts[1] === "new") {
            this.openCreate(parts[0], false);
          } else if (parts[2] === "edit") {
            this.openEdit(parts[0], parts[1], false);
          } else if (parts[0] === "resource") {
            this.openResource(parts[1], false);
          }
        },

        goHome() {
          window.location.hash = "";
        },

        async openResource(name, pushHash = true) {
          this.resource = name;
          this.view = "resource";
          if (pushHash) window.location.hash = `#/resource/${name}`;
          if (name === "comments") this.resourceItems = await this.api("/comments") || [];
          if (name === "taxonomies") this.resourceItems = await this.api("/taxonomies") || {};
          if (name === "menu") this.resourceItems = (await this.api("/menus/main") || {}).items || [];
          if (name === "schedule") {
            const scheduler = await this.api("/scheduler/jobs");
            this.resourceItems = scheduler?.items || [];
          }
        },

        async openWorkspace(section, pushHash = true) {
          const link = this.workspaceLinks.find((item) => item.name === section) || { label: section, description: "CMS workspace" };
          this.workspaceSection = section;
          this.workspaceTitle = link.label;
          this.workspaceDescription = link.description;
          this.view = "workspace";
          if (pushHash) window.location.hash = `#/workspace/${section}`;
          const result = await this.api(`/workspace/${encodeURIComponent(section)}`);
          if (result) {
            this.workspaceItems = Array.isArray(result.items) ? result.items : Object.entries(result.items || {}).map(([name, value]) => ({ name, value }));
            this.workspaceStats = result.stats || {};
          }
        },

        async moderateComment(id, status) {
          const result = await this.api(`/comments/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
          if (result) await this.openResource("comments", false);
        },

        async restoreRevision(typeName, itemId, revision) {
          const result = await this.api(`/${typeName}/items/${itemId}/restore/${revision}`, { method: "POST" });
          if (result) await this.openEdit(typeName, itemId);
        },

        showRevision(revision) {
          this.revisionCompare = revision;
        },

        async retrySchedule(jobId) {
          const result = await this.api(`/scheduler/jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST", body: "{}" });
          if (result) await this.openResource("schedule", false);
        },

        async openMediaPicker(fieldName) {
          this.mediaPickerField = fieldName;
          this.mediaItems = await this.api("/media") || [];
        },

        selectMedia(item) {
          if (this.mediaPickerField) this.formData[this.mediaPickerField] = item.url;
          this.mediaPickerField = null;
        },

        toDateTimeLocal(value) {
          if (!value) return "";
          const date = new Date(value);
          if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
          const pad = (part) => String(part).padStart(2, "0");
          return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
        },

        scheduleValue(value) {
          if (!value) return "";
          const date = new Date(value);
          return Number.isNaN(date.getTime()) ? "" : date.toISOString();
        },

        async saveMenu() {
          const result = await this.api("/menus/main", { method: "PUT", body: JSON.stringify(this.resourceItems) });
          if (result) this.resourceItems = result.items || [];
        },

        async createTaxonomy() {
          if (!this.taxonomyName.trim()) return;
          const result = await this.api("/taxonomies", { method: "POST", body: JSON.stringify({ name: this.taxonomyName.trim() }) });
          if (result) { this.taxonomyName = ""; this.resourceItems = result; }
        },
        async addTaxonomyTerm(name) {
          if (!this.taxonomyTerm.trim()) return;
          const result = await this.api(`/taxonomies/${encodeURIComponent(name)}`, { method: "POST", body: JSON.stringify({ term: this.taxonomyTerm.trim() }) });
          if (result) { this.taxonomyTerm = ""; this.resourceItems = result; }
        },
        async deleteTaxonomy(name) {
          const result = await this.api(`/taxonomies/${encodeURIComponent(name)}`, { method: "DELETE" });
          if (result) await this.openResource("taxonomies", false);
        },
        moveMenuItem(index, delta) {
          const target = index + delta;
          if (target < 0 || target >= this.resourceItems.length) return;
          const items = [...this.resourceItems];
          [items[index], items[target]] = [items[target], items[index]];
          this.resourceItems = items;
        },
        dropMenuItem(index) {
          if (this.dragMenuIndex === null || this.dragMenuIndex === index) return;
          this.moveMenuItem(this.dragMenuIndex, index > this.dragMenuIndex ? 1 : -1);
          this.dragMenuIndex = null;
        },

        findType(name) {
          return this.types.find((t) => t.name === name) || null;
        },

        can(action, type = this.currentType) {
          return Boolean(type?.capabilities?.[action]);
        },

        async openList(typeName, pushHash = true) {
          this.currentType = this.findType(typeName);
          if (!this.currentType) return;
          this.view = "list";
          this.selected = [];
          this.bulkAction = "";
          this.listQuery = { q: "" };
          this.listMeta.page = 1;
          if (pushHash) window.location.hash = `#/${typeName}`;
          await this.fetchList();
        },

        async fetchList() {
          if (!this.currentType) return;
          const params = new URLSearchParams();
          if (this.listQuery.q) params.set("q", this.listQuery.q);
          Object.keys(this.listQuery).forEach((k) => {
            if (k.startsWith("filter_") && this.listQuery[k]) params.set(k, this.listQuery[k]);
          });
          params.set("page", this.listMeta.page);
          const data = await this.api(`/${this.currentType.name}/items?` + params.toString());
          if (data) {
            this.listItems = data.items;
            this.listMeta = { total: data.total, page: data.page, pages: data.pages, per_page: data.per_page };
          }
        },

        changePage(delta) {
          const next = this.listMeta.page + delta;
          if (next < 1 || next > this.listMeta.pages) return;
          this.listMeta.page = next;
          this.fetchList();
        },

        toggleSelectAll(evt) {
          this.selected = evt.target.checked ? this.listItems.map((i) => i.id) : [];
        },

        async runBulkAction() {
          if (!this.can("update") || !this.bulkAction || !this.selected.length) return;
          const ok = await this.api(`/${this.currentType.name}/actions/${this.bulkAction}`, {
            method: "POST",
            body: JSON.stringify({ ids: this.selected }),
          });
          if (ok) {
            this.selected = [];
            this.bulkAction = "";
            await this.fetchList();
            await this.loadConfig();
          }
        },

        async deleteItem(id) {
          if (!this.can("delete")) return;
          if (!confirm("Delete this item?")) return;
          const ok = await this.api(`/${this.currentType.name}/items/${id}`, { method: "DELETE" });
          if (ok) {
            await this.fetchList();
            await this.loadConfig();
          }
        },

        openCreate(typeName, pushHash = true) {
          this.currentType = this.findType(typeName);
          if (!this.currentType || !this.can("create", this.currentType)) return;
          this.editingId = null;
          this.revisionCompare = null;
          this.formData = { status: "draft", slug: "" };
          this.currentType.fields.forEach((f) => {
            this.formData[f.name] = f.default !== undefined && f.default !== null
              ? f.default
              : (f.type === "boolean" ? false : (f.type === "select" ? ((f.choices || [])[0] || "draft") : (['json'].includes(f.type) ? "{}" : (['repeater','relationship'].includes(f.type) ? "[]" : ""))));
          });
          this.view = "form";
          this.dirty = false;
          this.restoreDraft(typeName);
          this.startAutosave();
          if (pushHash) window.location.hash = `#/${typeName}/new`;
        },

        async openEdit(typeName, itemId, pushHash = true) {
          this.currentType = this.findType(typeName);
          if (!this.currentType || !this.can("update", this.currentType)) return;
          const item = await this.api(`/${typeName}/items/${itemId}`);
          if (!item) return;
          this.editingId = itemId;
          this.revisionCompare = null;
          this.formData = { ...item };
          this.currentType.fields.filter((f) => ['json','repeater','relationship'].includes(f.type)).forEach((f) => { if (this.formData[f.name] !== undefined && typeof this.formData[f.name] !== 'string') this.formData[f.name] = JSON.stringify(this.formData[f.name], null, 2); });
          if (this.formData.publish_at) this.formData.publish_at = this.toDateTimeLocal(this.formData.publish_at);
          this.formData._history = await this.api(`/${typeName}/items/${itemId}/history`) || { items: [] };
          this.view = "form";
          this.dirty = false;
          this.restoreDraft(typeName, itemId);
          this.startAutosave();
          if (pushHash) window.location.hash = `#/${typeName}/${itemId}/edit`;
        },

        async saveItem() {
          if (!this.can(this.editingId ? "update" : "create")) return;
          const typeName = this.currentType.name;
          const payload = { ...this.formData };
          delete payload._history;
          if (payload.status === "scheduled") {
            payload.publish_at = this.scheduleValue(payload.publish_at);
            if (!payload.publish_at) {
              this.error = "Choose a valid publish date and time before scheduling this item.";
              return;
            }
          } else {
            delete payload.publish_at;
          }
          const hasUpload = this.currentType.fields.some((field) => ["file", "image"].includes(field.type));
          let body = JSON.stringify(payload);
          let headers = { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() };
          if (hasUpload) {
            const multipart = new FormData();
            Object.entries(payload).forEach(([key, value]) => multipart.append(key, value ?? ""));
            this.$root.querySelectorAll('input[type="file"]').forEach((input) => { if (input.files[0]) multipart.set(input.name, input.files[0]); });
            body = multipart;
            headers = { "X-CSRF-Token": csrfToken() };
          }
          if (this.editingId) {
            const ok = await this.api(`/${typeName}/items/${this.editingId}`, {
              method: "PUT",
              body,
              headers,
            });
            if (ok) { this.clearDraft(typeName, this.editingId); this.dirty = false; await this.openList(typeName); }
          } else {
            const ok = await this.api(`/${typeName}/items`, {
              method: "POST",
              body,
              headers,
            });
            if (ok) { this.clearDraft(typeName); this.dirty = false; await this.openList(typeName); }
          }
          await this.loadConfig();
        },

        draftKey(typeName, id = "new") { return `flaxon-cms-draft:${typeName}:${id}`; },
        startAutosave() {
          clearInterval(this.autosaveTimer);
          this.autosaveTimer = setInterval(() => {
            if (this.view === "form" && this.currentType && this.dirty) localStorage.setItem(this.draftKey(this.currentType.name, this.editingId || "new"), JSON.stringify(this.formData));
          }, 1000);
        },
        restoreDraft(typeName, id = "new") {
          try { const draft = JSON.parse(localStorage.getItem(this.draftKey(typeName, id)) || "null"); if (draft) { this.formData = { ...this.formData, ...draft }; this.dirty = true; } } catch (_) { this.error = "Saved draft could not be loaded."; }
        },
        clearDraft(typeName, id = "new") { localStorage.removeItem(this.draftKey(typeName, id || "new")); },

        formatCell(value) {
          if (value === null || value === undefined) return "";
          if (typeof value === "string" && value.length > 60) return value.slice(0, 57) + "...";
          return value;
        },

        exportUrl(format) {
          return `${API_BASE}/export/${this.currentType.name}?format=${format}`;
        },

        async importFile(event) {
          const file = event.target.files[0];
          if (!file || !this.currentType) return;
          try {
            const text = await file.text();
            let records;
            if (file.name.toLowerCase().endsWith('.csv')) {
              const rows = [];
              let row = [], cell = "", quoted = false;
              for (let index = 0; index < text.length; index++) {
                const char = text[index];
                const next = text[index + 1];
                if (char === '"' && quoted && next === '"') { cell += '"'; index++; }
                else if (char === '"') quoted = !quoted;
                else if (char === ',' && !quoted) { row.push(cell); cell = ""; }
                else if ((char === '\n' || char === '\r') && !quoted) {
                  if (char === '\r' && next === '\n') index++;
                  row.push(cell); rows.push(row); row = []; cell = "";
                } else cell += char;
              }
              if (cell || row.length) { row.push(cell); rows.push(row); }
              const [header, ...dataRows] = rows.filter((values) => values.some((value) => value !== ""));
              if (!header || !header.length) throw new Error("CSV file has no header row.");
              records = dataRows.map((values) => Object.fromEntries(header.map((key, index) => [key, values[index] || ""])));
            } else {
              records = JSON.parse(text);
            }
            if (!Array.isArray(records)) throw new Error("Import document must contain a list of records.");
            const result = await this.api(`/import/${this.currentType.name}`, { method: "POST", body: JSON.stringify(records) });
            if (result) await this.fetchList();
          } catch (error) {
            this.error = `Import failed: ${error.message}`;
          } finally {
            event.target.value = "";
          }
        },
      };
    }
