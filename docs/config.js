// BridgeLedger website settings.
// The publishable (anon) key is meant to be public: the database rules in
// supabase/schema.sql make sure each signed-in person can only read and
// change their own plan.
window.BRIDGE_SITE = {
  supabaseUrl: "https://kolqfaywmitujkiuxirv.supabase.co",
  supabaseAnonKey: "sb_publishable_b3QZvyzIdS_cobKASS8m0g_LCw4dh2w"
};
