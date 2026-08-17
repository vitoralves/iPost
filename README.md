# iPost

Personal Instagram publisher. Phase 0 proves Instagram Login, a public Supabase media URL, and one Story + one Reel publish.

## Local run

```bash
brew install ffmpeg
cp .env.example .env
```

Fill `.env` (never commit it):

- `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET` from the Meta app Instagram product (Instagram App ID, not the Facebook App ID)
- `INSTAGRAM_REDIRECT_URI=http://localhost:8000/auth/instagram/callback`
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

```bash
uv sync --package ipost-api
uv run --package ipost-api ipost-api
```

Open http://localhost:8000

## Meta app (required before Connect works)

Do **not** use [developers.meta.com](https://developers.meta.com) (Quest / Horizon). Use the **Meta App Dashboard**:

[https://developers.facebook.com/apps/](https://developers.facebook.com/apps/)

Official guide: [Create an Instagram app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)

1. Register as a Meta developer if prompted, then **Create App** (upper right).
2. **Connect a business** — skip / do later. Verification is only required to go live, not for your own account in Development.
3. **Use case** — choose **Other**, then Next. (If the wizard lists **Manage messaging and content on Instagram**, that also works.)
4. **App type** — **Business**, then Next. Instagram cannot be added to a consumer app.
5. Name the app (e.g. `iPost`) and a contact email, then create it.
6. On the dashboard, find **Instagram** (“Allow creators and businesses to manage messages and comments, publish content…”) and click **Set up**. Keep **API setup with Instagram login** (not Facebook login). You do not need a Facebook Page.
7. Under **Instagram → API setup with Instagram login**:
   - Add your Professional Instagram account (you will log in to Instagram).
   - Skip webhooks.
   - **Set up Instagram business login** → add OAuth redirect URI exactly:  
     `http://localhost:8000/auth/instagram/callback`  
     Check the saved list: the dashboard sometimes appends a trailing `/`.
8. Open **Business login settings** on that same page. Copy **Instagram App ID** and **Instagram App Secret** into `.env` as `INSTAGRAM_APP_ID` and `INSTAGRAM_APP_SECRET`. These are **not** the Meta app ID at the top of the dashboard.
9. Skip **App Review**. Development mode is enough for testers on the app.

Permissions we use: `instagram_business_basic`, `instagram_business_content_publish`.

## Phase 0 checklist

1. Connect Instagram on the local page
2. Create placeholder still → confirm the URL is `.../storage/v1/object/public/outbox/...` and opens in an incognito window
3. Publish Story
4. Create placeholder reel (needs ffmpeg) → same public URL check
5. Publish Reel

If Meta returns a fetch/download error, the URL is not publicly reachable. Stop and fix storage before building agents.
