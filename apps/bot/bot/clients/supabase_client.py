"""
Supabase client for the bot worker.

Uses service role key to bypass RLS — Railway only.
"""

from supabase import Client, create_client

from bot.config import Settings


def create_supabase_client(settings: Settings) -> Client:
    """Create a Supabase client with service role credentials."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
