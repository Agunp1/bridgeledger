# Put BridgeLedger online with email + password login

This gives you a public link, `https://agunp1.github.io/bridgeledger/`, where anyone can create an account and keep a private plan. About 10 minutes, all free.

## 1. Create the database (Supabase)

1. Go to **https://supabase.com** → **Start your project** → sign in with GitHub.
2. **New project** → name it `bridgeledger`, set a database password (save it somewhere), pick the region closest to you → **Create new project**. Wait about a minute.
3. Left menu → **SQL Editor** → **New query** → paste everything from [`supabase/schema.sql`](supabase/schema.sql) → **Run**. You should see "Success. No rows returned".
4. Left menu → **Authentication** → **URL Configuration**:
   - **Site URL:** `https://agunp1.github.io/bridgeledger/`
   - **Redirect URLs** → **Add URL:** `https://agunp1.github.io/bridgeledger/`
   - **Save**. (This makes confirmation and password-reset emails link back to the site.)
5. Left menu → **Project Settings** → **API** (or **Data API**). Copy two things:
   - **Project URL** (looks like `https://abcdefgh.supabase.co`)
   - **anon public** key (a long text starting with `eyJ...`, or `sb_publishable_...`)

   The anon key is safe to make public. Never copy the `service_role` / secret key anywhere.

## 2. Add the two values to the site

Open [`docs/config.js`](docs/config.js) on GitHub → pencil icon (Edit) → paste the two values between the quotes → **Commit changes**.

```js
window.BRIDGE_SITE = {
  supabaseUrl: "https://abcdefgh.supabase.co",
  supabaseAnonKey: "eyJ..."
};
```

## 3. Turn on GitHub Pages

Repository → **Settings** → **Pages** → under **Build and deployment**: Source **Deploy from a branch**, Branch **main**, folder **/docs** → **Save**. After a minute or two the page shows your link: `https://agunp1.github.io/bridgeledger/`.

## 4. Try it

Open the link → **Sign in** → **Create account** with your email and a password (8+ characters) → click the confirmation link in your email → sign in. Your plan now saves to your account. Send the same link to friends: each person gets their own private plan.

## How privacy works

- Passwords are handled by Supabase Auth and stored only as secure hashes. The app never sees or stores them.
- Each person's plan is one row in the `plans` table. The row-level security rules in `schema.sql` allow a signed-in person to read and change only their own row. Visitors who aren't signed in can't read anything.
- To delete an account: Supabase → Authentication → Users → the user → Delete. Their plan is deleted with it.

## Updating the site

The website is built from `web/index.html`, the same file behind the Claude link:

```bash
python scripts/build_site.py
```

This rewrites `docs/index.html` and keeps your `docs/config.js`. Commit and push, and GitHub Pages updates within a minute. Market rates live in `docs/market.json`, updated weekly by the scheduled refresh.
