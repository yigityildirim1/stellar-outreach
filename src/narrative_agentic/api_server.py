#!/usr/bin/env python3
"""
NEXUS STATION API Server

HTTP server that bridges the frontend with the Python backend.
Provides endpoints for the NEXUS agent to process messages.
"""

import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative_agentic import (
    create_nexus_agent,
    NexusAgent,
    auto_configure_with_defaults,
    get_api_config,
    get_config_manager,
)
from narrative_agentic.actions import execute_confirmed_action
from narrative_agentic.stellar_outreach.discovery_cards import (
    fetch_daily_card,
    get_card_collection,
    collect_card,
)

# Global agent instance (initialized on first request)
_agent = None
_agent_lock = threading.Lock()


def get_agent() -> NexusAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                # Ensure APIs are configured
                config_status = get_config_manager().is_configured()
                if not config_status['fully_configured']:
                    print("[SERVER] Configuring APIs...")
                    auto_configure_with_defaults()
                
                _agent = create_nexus_agent()
                print("[SERVER] NEXUS Agent initialized")
    return _agent


class CORSRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler with CORS support."""
    
    def _set_headers(self, content_type="application/json"):
        """Set response headers."""
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS request for CORS."""
        self._set_headers()
    
    def _send_json(self, data: dict):
        """Send JSON response."""
        self._set_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, message: str, status: int = 500):
        """Send error response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Status endpoint
        if path == "/api/status":
            try:
                agent = get_agent()
                status = agent.get_status()
                config = get_api_config()
                
                self._send_json({
                    "status": "ok",
                    "agent": status,
                    "config": {
                        "openai_model": config.openai_coding_model,
                        "gemini_model": config.gemini_general_model,
                        "openai_configured": bool(config.openai_api_key),
                        "gemini_configured": bool(config.gemini_api_key),
                    }
                })
            except Exception as e:
                self._send_error(str(e))
            return
        
        # Crew endpoint
        if path == "/api/crew":
            try:
                agent = get_agent()
                crew_list = []
                for member in agent.crew:
                    crew_list.append({
                        "name": member.name,
                        "role": member.role,
                        "catchphrase": member.catchphrase,
                        "marker": member.marker,
                        "triggers": member.consultation_triggers[:6],
                    })
                
                self._send_json({"crew": crew_list})
            except Exception as e:
                self._send_error(str(e))
            return
        
        # Precedents endpoint
        if path == "/api/precedents":
            try:
                agent = get_agent()
                precedents = []
                
                # Get recent precedents
                recent = sorted(
                    agent.precedent_log.precedents.values(),
                    key=lambda p: p.created_at,
                    reverse=True
                )[:10]
                
                for p in recent:
                    precedents.append({
                        "id": p.id,
                        "title": p.title,
                        "type": p.precedent_type.value,
                        "status": p.status.value,
                        "loop": p.loop_number,
                    })
                
                self._send_json({"precedents": precedents})
            except Exception as e:
                self._send_error(str(e))
            return
        
        # Tasks endpoint (Mission Log)
        if path == "/api/tasks":
            try:
                agent = get_agent()
                query = parse_qs(parsed.query)
                assigned_to = query.get('assigned_to', [None])[0]
                status = query.get('status', [None])[0]

                tasks = agent.get_tasks(assigned_to, status)
                tasks_data = []
                for t in tasks:
                    tasks_data.append({
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "assigned_to": t.assigned_to,
                        "status": t.status,
                        "priority": t.priority,
                        "created_at": t.created_at,
                        "updated_at": t.updated_at,
                        "completed_at": t.completed_at,
                        "comments": t.comments,
                    })

                self._send_json({"tasks": tasks_data})
            except Exception as e:
                self._send_error(str(e))
            return

        # Communications endpoint (Comms)
        if path == "/api/comms":
            try:
                agent = get_agent()
                query = parse_qs(parsed.query)
                unread_only = query.get('unread_only', ['false'])[0] == 'true'
                from_member = query.get('from_member', [None])[0]

                comms = agent.memory_manager.get_communications(unread_only, from_member)
                comms_data = []
                for c in comms:
                    comms_data.append({
                        "id": c.id,
                        "subject": c.subject,
                        "content": c.content,
                        "from_member": c.from_member,
                        "type": c.type,
                        "priority": c.priority,
                        "timestamp": c.timestamp,
                        "read": c.read,
                        "starred": c.starred,
                    })

                self._send_json({"communications": comms_data})
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Discovery Card endpoint
        if path == "/api/stellar/discovery-card":
            try:
                query = parse_qs(parsed.query)
                date_param = query.get('date', [None])[0]
                card = fetch_daily_card(date_str=date_param)
                self._send_json(card.to_dict())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Sky Today (universal transit snapshot)
        if path == "/api/stellar/sky-today":
            try:
                from narrative_agentic.stellar_outreach.transit_engine import (
                    get_transit_snapshot,
                    transit_snapshot_to_dict,
                )
                query = parse_qs(parsed.query)
                date_param = query.get('date', [None])[0]
                snapshot = get_transit_snapshot(date_str=date_param)
                self._send_json(transit_snapshot_to_dict(snapshot))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Card collection stats
        if path == "/api/stellar/collection":
            try:
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', ['default'])[0]
                collection = get_card_collection(player_id)
                self._send_json(collection.get_stats())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Station state
        if path == "/api/stellar/station":
            try:
                from narrative_agentic.stellar_outreach.station_modules import (
                    get_station,
                    station_to_dict,
                )
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                station = get_station(player_id)
                if station is None:
                    self._send_error("Station not found", 404)
                    return
                self._send_json(station_to_dict(station))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Daily Mission
        if path == "/api/stellar/daily-mission":
            try:
                from narrative_agentic.stellar_outreach.mini_games import (
                    generate_daily_mission as _gen_daily,
                    daily_mission_to_dict as _dm_to_dict,
                )
                query = parse_qs(parsed.query)
                # Accept optional module_statuses as JSON in query param
                # or generate with empty statuses
                player_id = query.get('player_id', ['default'])[0]
                date_param = query.get('date', [None])[0]
                mission = _gen_daily(module_statuses=[], date_str=date_param)
                self._send_json(_dm_to_dict(mission))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Notification history
        if path == "/api/stellar/notifications/history":
            try:
                from narrative_agentic.stellar_outreach.notifications import (
                    get_notification_history as _get_notif_history,
                    notification_to_dict as _notif_to_dict,
                )
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                limit = int(query.get('limit', ['20'])[0])
                history = _get_notif_history(player_id, limit=limit)
                self._send_json({
                    "player_id": player_id,
                    "notifications": [_notif_to_dict(n) for n in history],
                    "count": len(history),
                })
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Notification preferences (GET)
        if path == "/api/stellar/notifications/preferences":
            try:
                from narrative_agentic.stellar_outreach.notifications import (
                    get_preferences as _get_notif_prefs,
                    preferences_to_dict as _prefs_to_dict,
                )
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                prefs = _get_notif_prefs(player_id)
                self._send_json(_prefs_to_dict(prefs))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Friends list (TASK-010)
        if path == "/api/stellar/friends":
            try:
                from narrative_agentic.stellar_outreach.friends import get_friends as _get_friends
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(_get_friends(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Friend requests (TASK-010)
        if path == "/api/stellar/friends/requests":
            try:
                from narrative_agentic.stellar_outreach.friends import get_friend_requests as _get_freq
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(_get_freq(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Streak data (TASK-012)
        if path == "/api/stellar/streak":
            try:
                from narrative_agentic.stellar_outreach.streaks import get_streak as _get_streak
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(_get_streak(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Streak rewards (TASK-012)
        if path == "/api/stellar/streak/rewards":
            try:
                from narrative_agentic.stellar_outreach.streaks import get_streak_rewards as _get_sr
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(_get_sr(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: NPC list (TASK-009)
        if path == "/api/stellar/npc/list":
            try:
                from narrative_agentic.stellar_outreach.npc_crew import get_npc_list
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_npc_list(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: NPC detail (TASK-009)
        if path == "/api/stellar/npc/detail":
            try:
                from narrative_agentic.stellar_outreach.npc_crew import get_npc_detail
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                npc_id = query.get('npc_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                if not npc_id:
                    self._send_error("npc_id query parameter required", 400)
                    return
                self._send_json(get_npc_detail(player_id, npc_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: NPC active perks (TASK-009)
        if path == "/api/stellar/npc/perks":
            try:
                from narrative_agentic.stellar_outreach.npc_crew import get_active_perks
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_active_perks(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild details (TASK-011)
        if path == "/api/stellar/guild":
            try:
                from narrative_agentic.stellar_outreach.guilds import get_guild
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_guild(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Weekly challenge (TASK-011)
        if path == "/api/stellar/guild/challenge":
            try:
                from narrative_agentic.stellar_outreach.guilds import get_weekly_challenge
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_weekly_challenge(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Star Atlas (TASK-013)
        if path == "/api/stellar/atlas":
            try:
                from narrative_agentic.stellar_outreach.star_atlas import get_atlas
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_atlas(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Atlas category (TASK-013)
        if path == "/api/stellar/atlas/category":
            try:
                from narrative_agentic.stellar_outreach.star_atlas import get_atlas_category
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                category = query.get('category', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                if not category:
                    self._send_error("category query parameter required", 400)
                    return
                self._send_json(get_atlas_category(player_id, category))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mission archive (TASK-013)
        if path == "/api/stellar/atlas/missions":
            try:
                from narrative_agentic.stellar_outreach.star_atlas import get_mission_archive
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_mission_archive(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Cosmic passport (TASK-013)
        if path == "/api/stellar/atlas/passport":
            try:
                from narrative_agentic.stellar_outreach.star_atlas import get_cosmic_passport
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_cosmic_passport(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Station customization (TASK-014)
        if path == "/api/stellar/customization":
            try:
                from narrative_agentic.stellar_outreach.station_customization import get_customization
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                sun_sign = query.get('sun_sign', [''])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_customization(player_id, sun_sign))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Available skins (TASK-014)
        if path == "/api/stellar/customization/skins":
            try:
                from narrative_agentic.stellar_outreach.station_customization import get_available_skins
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_available_skins(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Available decorations (TASK-014)
        if path == "/api/stellar/customization/decorations":
            try:
                from narrative_agentic.stellar_outreach.station_customization import get_available_decorations
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_available_decorations(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Preview skin (TASK-014)
        if path == "/api/stellar/customization/preview":
            try:
                from narrative_agentic.stellar_outreach.station_customization import preview_skin
                query = parse_qs(parsed.query)
                skin_id = query.get('skin_id', [None])[0]
                element = query.get('element', [''])[0]
                if not skin_id:
                    self._send_error("skin_id query parameter required", 400)
                    return
                self._send_json(preview_skin(skin_id, element))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Element palette (TASK-014)
        if path == "/api/stellar/customization/palette":
            try:
                from narrative_agentic.stellar_outreach.station_customization import get_element_palette
                query = parse_qs(parsed.query)
                sun_sign = query.get('sun_sign', [None])[0]
                if not sun_sign:
                    self._send_error("sun_sign query parameter required", 400)
                    return
                self._send_json(get_element_palette(sun_sign))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Store catalog (TASK-015)
        if path == "/api/stellar/store/catalog":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_store_catalog
                query = parse_qs(parsed.query)
                category = query.get('category', [None])[0]
                rarity = query.get('rarity', [None])[0]
                tag = query.get('tag', [None])[0]
                self._send_json(get_store_catalog(category, rarity, tag))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Featured items (TASK-015)
        if path == "/api/stellar/store/featured":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_featured_items
                self._send_json(get_featured_items())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Player wallet (TASK-015)
        if path == "/api/stellar/store/wallet":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_wallet
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_wallet(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Transaction history (TASK-015)
        if path == "/api/stellar/store/history":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_transaction_history
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                limit = int(query.get('limit', ['20'])[0])
                offset = int(query.get('offset', ['0'])[0])
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_transaction_history(player_id, limit, offset))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Gem packs (TASK-015)
        if path == "/api/stellar/store/packs":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_gem_packs
                self._send_json(get_gem_packs())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Store summary (TASK-015)
        if path == "/api/stellar/store/summary":
            try:
                from narrative_agentic.stellar_outreach.cosmetic_store import get_store_summary
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_store_summary(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Pass status (TASK-016)
        if path == "/api/stellar/pass/status":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_pass_status
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_pass_status(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Current season info (TASK-016)
        if path == "/api/stellar/pass/season":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_season_info
                self._send_json(get_season_info())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Season progress (TASK-016)
        if path == "/api/stellar/pass/progress":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_season_progress
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_season_progress(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Season rewards / tiers (TASK-016)
        if path == "/api/stellar/pass/rewards":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_season_rewards
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_season_rewards(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Active benefits (TASK-016)
        if path == "/api/stellar/pass/benefits":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_pass_benefits
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_pass_benefits(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Subscription products (TASK-016)
        if path == "/api/stellar/pass/products":
            try:
                from narrative_agentic.stellar_outreach.cosmic_pass import get_subscription_products
                self._send_json(get_subscription_products())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Ad status (TASK-017)
        if path == "/api/stellar/ads/status":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import get_ad_status
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_ad_status(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Available ad placements (TASK-017)
        if path == "/api/stellar/ads/placements":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import get_available_placements
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_available_placements(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Ad config (TASK-017)
        if path == "/api/stellar/ads/config":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import get_ad_config
                self._send_json(get_ad_config())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Ad history (TASK-017)
        if path == "/api/stellar/ads/history":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import get_ad_history
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                limit = int(query.get('limit', ['20'])[0])
                offset = int(query.get('offset', ['0'])[0])
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_ad_history(player_id, limit, offset))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Ad stats (TASK-017)
        if path == "/api/stellar/ads/stats":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import get_ad_stats
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_ad_stats(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: ISS current position
        if path == "/api/stellar/iss/current":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_iss_current
                self._send_json(get_iss_current())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: ISS pass predictions
        if path == "/api/stellar/iss/passes":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_iss_passes
                query = parse_qs(parsed.query)
                lat = float(query.get('lat', [0])[0])
                lng = float(query.get('lng', [0])[0])
                days = int(query.get('days', [5])[0])
                self._send_json(get_iss_passes(lat, lng, days))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Visible sky objects
        if path == "/api/stellar/sky/visible":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_visible_sky
                query = parse_qs(parsed.query)
                lat = float(query.get('lat', [0])[0])
                lng = float(query.get('lng', [0])[0])
                timestamp = query.get('timestamp', [None])[0]
                self._send_json(get_visible_sky(lat, lng, timestamp))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Sky snapshot (full state)
        if path == "/api/stellar/sky/snapshot":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_sky_snapshot
                query = parse_qs(parsed.query)
                lat = float(query.get('lat', [0])[0])
                lng = float(query.get('lng', [0])[0])
                player_id = query.get('player_id', ['default'])[0]
                self._send_json(get_sky_snapshot(lat, lng, player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Constellation detail
        if path.startswith("/api/stellar/sky/constellation/"):
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_constellation_detail
                constellation_id = path.split("/")[-1]
                query = parse_qs(parsed.query)
                lat = float(query.get('lat', [0])[0])
                lng = float(query.get('lng', [0])[0])
                self._send_json(get_constellation_detail(constellation_id, lat, lng))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Sky scanner config
        if path == "/api/stellar/sky/config":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_sky_config
                self._send_json(get_sky_config())
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: AR session history
        if path == "/api/stellar/sky/history":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import get_ar_history
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [None])[0]
                if not player_id:
                    self._send_error("player_id query parameter required", 400)
                    return
                self._send_json(get_ar_history(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Active astronomical events (TASK-019)
        if path == "/api/stellar/events/active":
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_active_events
                query = parse_qs(parsed.query)
                lat = query.get('lat', [None])[0]
                lng = query.get('lng', [None])[0]
                lat = float(lat) if lat else None
                lng = float(lng) if lng else None
                self._send_json(get_active_events(lat, lng))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Upcoming astronomical events
        if path == "/api/stellar/events/upcoming":
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_upcoming_events
                query = parse_qs(parsed.query)
                lat = query.get('lat', [None])[0]
                lng = query.get('lng', [None])[0]
                days = int(query.get('days', [30])[0])
                lat = float(lat) if lat else None
                lng = float(lng) if lng else None
                self._send_json(get_upcoming_events(lat, lng, days))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Event detail by ID
        if path.startswith("/api/stellar/events/detail/"):
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_event_detail
                event_id = path.split("/")[-1]
                self._send_json(get_event_detail(event_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Event calendar
        if path == "/api/stellar/events/calendar":
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_event_calendar
                from datetime import date as _date_now
                query = parse_qs(parsed.query)
                _today = _date_now.today()
                year = int(query.get('year', [_today.year])[0])
                month = int(query.get('month', [_today.month])[0])
                self._send_json(get_event_calendar(year, month))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Event bonuses for player
        if path == "/api/stellar/events/bonuses":
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_event_bonuses
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', ['default'])[0]
                self._send_json(get_event_bonuses(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Event system config
        if path == "/api/stellar/events/config":
            try:
                from narrative_agentic.stellar_outreach.astronomical_events import get_event_config
                self._send_json(get_event_config())
            except Exception as e:
                self._send_error(str(e))
            return

        # ─── Auth: check player ─────────────────────────────────
        if path == "/api/auth/check":
            try:
                from narrative_agentic.stellar_outreach.auth import check_player
                query = parse_qs(parsed.query)
                player_id = query.get('player_id', [''])[0]
                if not player_id:
                    self._send_error("player_id query param required", 400)
                    return
                self._send_json(check_player(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Default - 404
        self._send_error("Not found", 404)

    def do_PUT(self):
        """Handle PUT requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
            return

        # Update task status
        if path.startswith("/api/tasks/"):
            task_id = path.split("/")[-1]
            new_status = data.get('status')

            if not new_status:
                self._send_error("Status required", 400)
                return

            try:
                agent = get_agent()
                task = agent.update_task_status(task_id, new_status)
                if task:
                    self._send_json({
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "updated_at": task.updated_at,
                    })
                else:
                    self._send_error("Task not found", 404)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Update notification preferences (PUT)
        if path == "/api/stellar/notifications/preferences":
            from narrative_agentic.stellar_outreach.notifications import (
                update_preferences as _update_notif_prefs,
                preferences_to_dict as _prefs_to_dict2,
            )

            player_id = data.get('player_id', '')
            if not player_id:
                self._send_error("player_id is required", 400)
                return

            # All other fields are optional updates
            updates = {k: v for k, v in data.items() if k != 'player_id'}

            try:
                prefs = _update_notif_prefs(player_id, updates)
                self._send_json(_prefs_to_dict2(prefs))
            except Exception as e:
                self._send_error(str(e))
            return

        # Update communication (read/starred)
        if path.startswith("/api/comms/"):
            comm_id = path.split("/")[-1]

            try:
                agent = get_agent()

                if data.get('starred'):
                    comm = agent.memory_manager.toggle_communication_starred(comm_id)
                else:
                    comm = agent.memory_manager.mark_communication_read(comm_id)

                if comm:
                    self._send_json({
                        "id": comm.id,
                        "read": comm.read,
                        "starred": comm.starred,
                    })
                else:
                    self._send_error("Communication not found", 404)
            except Exception as e:
                self._send_error(str(e))
            return

        # Default - 404
        self._send_error("Not found", 404)

    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Delete all tasks
        if path == "/api/tasks":
            try:
                agent = get_agent()
                count = agent.delete_all_tasks()
                self._send_json({"deleted": count})
            except Exception as e:
                self._send_error(str(e))
            return

        # Delete single task
        if path.startswith("/api/tasks/"):
            task_id = path.split("/")[-1]
            try:
                agent = get_agent()
                success = agent.delete_task(task_id)
                if success:
                    self._send_json({"deleted": task_id})
                else:
                    self._send_error("Task not found", 404)
            except Exception as e:
                self._send_error(str(e))
            return

        self._send_error("Not found", 404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
            return
        
        # Process message endpoint
        if path == "/api/chat":
            message = data.get('message', '')
            
            if not message:
                self._send_error("Message required", 400)
                return
            
            try:
                agent = get_agent()
                response = agent.process(message)
                
                # Build crew responses for JSON
                crew_responses_data = []
                for cr in response.crew_responses:
                    crew_responses_data.append({
                        "name": cr.name,
                        "role": cr.role,
                        "marker": cr.marker,
                        "catchphrase": cr.catchphrase,
                        "content": cr.content,
                    })
                
                # Build direct crew response if present
                direct_crew_data = None
                if response.direct_crew_response:
                    dcr = response.direct_crew_response
                    direct_crew_data = {
                        "name": dcr.name,
                        "role": dcr.role,
                        "marker": dcr.marker,
                        "catchphrase": dcr.catchphrase,
                        "content": dcr.content,
                    }
                
                self._send_json({
                    "content": response.content,
                    "from_api": response.from_api,
                    "model": response.model,
                    "crew_consulted": response.crew_consulted,
                    "crew_responses": crew_responses_data,
                    "direct_crew_response": direct_crew_data,
                    "tokens_used": int(response.budget_spent),
                    "precedent": response.precedent_established,
                    "actions_taken": response.actions_taken,
                    "pending_actions": response.pending_actions,
                })
                
                # Advance loop
                agent.next_loop()
                
            except Exception as e:
                self._send_error(str(e))
            return
        
        # Create task endpoint
        if path == "/api/tasks":
            title = data.get('title', '')
            description = data.get('description', '')
            assigned_to = data.get('assigned_to', 'NEXUS')
            priority = data.get('priority', 'MEDIUM')

            if not title:
                self._send_error("Title required", 400)
                return

            try:
                agent = get_agent()
                task = agent.create_task(title, description, assigned_to, priority)
                self._send_json({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "assigned_to": task.assigned_to,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at,
                })
            except Exception as e:
                self._send_error(str(e))
            return

        # Create communication endpoint
        if path == "/api/comms":
            subject = data.get('subject', '')
            content = data.get('content', '')
            from_member = data.get('from_member', 'NEXUS')
            comm_type = data.get('type', 'UPDATE')
            priority = data.get('priority', 'NORMAL')

            if not subject or not content:
                self._send_error("Subject and content required", 400)
                return

            try:
                agent = get_agent()
                comm = agent.memory_manager.create_communication(
                    subject, content, from_member, comm_type, priority
                )
                self._send_json({
                    "id": comm.id,
                    "subject": comm.subject,
                    "from_member": comm.from_member,
                    "type": comm.type,
                    "timestamp": comm.timestamp,
                })
            except Exception as e:
                self._send_error(str(e))
            return

        # Session summary endpoint
        if path == "/api/summary":
            try:
                agent = get_agent()
                result = agent.generate_session_summary()
                if result:
                    self._send_json({"status": "ok", "summary": result})
                else:
                    self._send_error("No session history to summarize", 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Confirm pending action (Article V gate)
        if path == "/api/actions/confirm":
            action_id = data.get('action_id', '')
            approved = data.get('approved', False)

            if not action_id:
                self._send_error("action_id required", 400)
                return

            if not approved:
                self._send_json({
                    "status": "rejected",
                    "action_id": action_id,
                    "summary": "Action rejected by Director.",
                })
                return

            try:
                agent = get_agent()
                result = execute_confirmed_action(action_id, agent.memory_manager)
                self._send_json({
                    "status": "executed",
                    "action_id": action_id,
                    "success": result.success,
                    "action_type": result.action_type,
                    "summary": result.summary,
                    "details": result.details,
                })
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Birth Chart endpoint
        if path == "/api/stellar/birth-chart":
            from datetime import date as _date, time as _time
            from narrative_agentic.stellar_outreach.birth_chart import (
                BirthChartInput,
                calculate_birth_chart,
                player_profile_to_dict,
            )

            birth_date_str = data.get('birth_date', '')
            birth_time_str = data.get('birth_time')  # optional
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            # Validate required fields
            if not birth_date_str:
                self._send_error("birth_date is required (YYYY-MM-DD)", 400)
                return
            if latitude is None or longitude is None:
                self._send_error("latitude and longitude are required", 400)
                return

            try:
                bd = _date.fromisoformat(birth_date_str)
            except (ValueError, TypeError):
                self._send_error("Invalid birth_date format. Use YYYY-MM-DD.", 400)
                return

            bt = None
            if birth_time_str:
                try:
                    parts = birth_time_str.split(':')
                    bt = _time(int(parts[0]), int(parts[1]))
                except (ValueError, TypeError, IndexError):
                    self._send_error("Invalid birth_time format. Use HH:MM.", 400)
                    return

            try:
                lat = float(latitude)
                lon = float(longitude)
            except (ValueError, TypeError):
                self._send_error("latitude and longitude must be numbers", 400)
                return

            try:
                chart_input = BirthChartInput(
                    birth_date=bd,
                    latitude=lat,
                    longitude=lon,
                    birth_time=bt,
                )
                profile = calculate_birth_chart(chart_input)
                self._send_json(player_profile_to_dict(profile))
            except ValueError as e:
                self._send_error(str(e), 400)
            except RuntimeError as e:
                self._send_error(str(e), 500)
            except Exception as e:
                self._send_error(f"Chart calculation error: {e}", 500)
            return

        # Stellar Outreach: Daily Briefing (personalized transit overlay)
        if path == "/api/stellar/daily-briefing":
            from datetime import date as _date, time as _time
            from narrative_agentic.stellar_outreach.birth_chart import (
                BirthChartInput,
                calculate_birth_chart,
            )
            from narrative_agentic.stellar_outreach.transit_engine import (
                calculate_player_transits,
                cosmic_briefing_to_dict,
            )

            birth_date_str = data.get('birth_date', '')
            birth_time_str = data.get('birth_time')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            transit_date = data.get('transit_date')  # optional

            if not birth_date_str:
                self._send_error("birth_date is required (YYYY-MM-DD)", 400)
                return
            if latitude is None or longitude is None:
                self._send_error("latitude and longitude are required", 400)
                return

            try:
                bd = _date.fromisoformat(birth_date_str)
            except (ValueError, TypeError):
                self._send_error("Invalid birth_date format. Use YYYY-MM-DD.", 400)
                return

            bt = None
            if birth_time_str:
                try:
                    parts = birth_time_str.split(':')
                    bt = _time(int(parts[0]), int(parts[1]))
                except (ValueError, TypeError, IndexError):
                    self._send_error("Invalid birth_time format. Use HH:MM.", 400)
                    return

            try:
                lat = float(latitude)
                lon = float(longitude)
            except (ValueError, TypeError):
                self._send_error("latitude and longitude must be numbers", 400)
                return

            try:
                chart_input = BirthChartInput(
                    birth_date=bd,
                    latitude=lat,
                    longitude=lon,
                    birth_time=bt,
                )
                profile = calculate_birth_chart(chart_input)
                briefing = calculate_player_transits(profile, date_str=transit_date)
                self._send_json(cosmic_briefing_to_dict(briefing))
            except ValueError as e:
                self._send_error(str(e), 400)
            except RuntimeError as e:
                self._send_error(str(e), 500)
            except Exception as e:
                self._send_error(f"Transit calculation error: {e}", 500)
            return

        # Stellar Outreach: Full Daily Briefing (TASK-005)
        if path == "/api/stellar/briefing":
            from narrative_agentic.stellar_outreach.cosmic_briefing import (
                generate_daily_briefing as _gen_briefing,
                briefing_to_dict as _briefing_to_dict,
            )

            player_id = data.get('player_id', '')
            if not player_id:
                self._send_error("player_id is required", 400)
                return

            birth_input = None
            birth_date_str = data.get('birth_date', '')
            if birth_date_str:
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                if latitude is None or longitude is None:
                    self._send_error("latitude and longitude are required with birth_date", 400)
                    return
                birth_input = {
                    "birth_date": birth_date_str,
                    "birth_time": data.get('birth_time'),
                    "latitude": latitude,
                    "longitude": longitude,
                }

            transit_date = data.get('transit_date')

            try:
                briefing = _gen_briefing(
                    player_id=player_id,
                    birth_input=birth_input,
                    date_str=transit_date,
                )
                self._send_json(_briefing_to_dict(briefing))
            except ValueError as e:
                self._send_error(str(e), 400)
            except RuntimeError as e:
                self._send_error(str(e), 500)
            except Exception as e:
                self._send_error(f"Briefing generation error: {e}", 500)
            return

        # Stellar Outreach: Create station
        if path == "/api/stellar/station":
            from narrative_agentic.stellar_outreach.station_modules import (
                create_station as _create_station,
                station_to_dict as _station_to_dict,
            )

            player_id = data.get('player_id', '')
            station_name = data.get('station_name', '')

            if not player_id:
                self._send_error("player_id is required", 400)
                return
            if not station_name:
                self._send_error("station_name is required", 400)
                return

            try:
                station = _create_station(player_id, station_name)
                self._send_json(_station_to_dict(station))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Collect resources
        if path == "/api/stellar/station/collect":
            from narrative_agentic.stellar_outreach.station_modules import (
                get_station as _get_station,
                collect_resources as _collect_resources,
                save_station as _save_station,
                station_to_dict as _station_to_dict2,
            )

            player_id = data.get('player_id', '')
            if not player_id:
                self._send_error("player_id is required", 400)
                return

            try:
                station = _get_station(player_id)
                if station is None:
                    self._send_error("Station not found", 404)
                    return
                collected = _collect_resources(station)
                _save_station(station)
                self._send_json({
                    "collected": collected,
                    "total_resources": station.resources,
                })
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Upgrade module
        if path == "/api/stellar/station/upgrade":
            from narrative_agentic.stellar_outreach.station_modules import (
                get_station as _get_station_u,
                upgrade_module as _upgrade_module,
                save_station as _save_station_u,
                station_to_dict as _station_to_dict3,
            )

            player_id = data.get('player_id', '')
            module_id = data.get('module_id', '')

            if not player_id:
                self._send_error("player_id is required", 400)
                return
            if not module_id:
                self._send_error("module_id is required", 400)
                return

            try:
                station = _get_station_u(player_id)
                if station is None:
                    self._send_error("Station not found", 404)
                    return
                success = _upgrade_module(station, module_id)
                if success:
                    _save_station_u(station)
                    self._send_json({
                        "success": True,
                        "module_id": module_id,
                        "new_level": station.modules[module_id].level,
                        "station": _station_to_dict3(station),
                    })
                else:
                    self._send_json({
                        "success": False,
                        "module_id": module_id,
                        "reason": "Insufficient resources or max level reached",
                    })
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Star Pattern (generate)
        if path == "/api/stellar/mini-game/star-pattern":
            from narrative_agentic.stellar_outreach.mini_games import generate_star_puzzle as _gen_sp
            from dataclasses import asdict
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                puzzle = _gen_sp(difficulty=diff, module_level=mlvl)
                result = asdict(puzzle)
                # Convert tuple connections to lists for JSON
                result["connections"] = [list(c) for c in result["connections"]]
                result["revealed_connections"] = [list(c) for c in result["revealed_connections"]]
                result["hidden_connections"] = [list(c) for c in result["hidden_connections"]]
                self._send_json(result)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Star Pattern (score)
        if path == "/api/stellar/mini-game/star-pattern/score":
            from narrative_agentic.stellar_outreach.mini_games import score_star_puzzle as _score_sp
            from dataclasses import asdict as _asdict2
            try:
                puzzle_id = data.get('puzzle_id', '')
                player_connections = data.get('player_connections', [])
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_sp(puzzle_id, player_connections, time_taken, cosmic_buff)
                self._send_json(_asdict2(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Repair Puzzle (generate)
        if path == "/api/stellar/mini-game/repair":
            from narrative_agentic.stellar_outreach.mini_games import generate_repair_puzzle as _gen_rp
            from dataclasses import asdict as _asdict3
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                grid = _gen_rp(difficulty=diff, module_level=mlvl)
                self._send_json(_asdict3(grid))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Repair Puzzle (score)
        if path == "/api/stellar/mini-game/repair/score":
            from narrative_agentic.stellar_outreach.mini_games import validate_repair_solution as _val_rp
            from dataclasses import asdict as _asdict4
            try:
                puzzle_id = data.get('puzzle_id', '')
                paths = data.get('paths', [])
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _val_rp(puzzle_id, paths, time_taken, cosmic_buff)
                self._send_json(_asdict4(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Asteroid Deflection (generate)
        if path == "/api/stellar/mini-game/asteroid":
            from narrative_agentic.stellar_outreach.mini_games import generate_asteroid_scenario as _gen_ad
            from dataclasses import asdict as _asdict5
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                scenario = _gen_ad(difficulty=diff, module_level=mlvl)
                self._send_json(_asdict5(scenario))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Asteroid Deflection (score)
        if path == "/api/stellar/mini-game/asteroid/score":
            from narrative_agentic.stellar_outreach.mini_games import score_deflection as _score_ad
            from dataclasses import asdict as _asdict6
            try:
                scenario_id = data.get('scenario_id', '')
                player_angle = float(data.get('player_angle', 0))
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_ad(scenario_id, player_angle, time_taken, cosmic_buff)
                self._send_json(_asdict6(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Generate morning briefing notification
        if path == "/api/stellar/notifications/morning":
            from narrative_agentic.stellar_outreach.notifications import (
                generate_morning_briefing as _gen_morning,
                notification_to_dict as _notif_to_dict2,
            )

            player_id = data.get('player_id', '')
            module_statuses = data.get('module_statuses', [])

            if not player_id:
                self._send_error("player_id is required", 400)
                return

            try:
                notif = _gen_morning(player_id, module_statuses)
                self._send_json(_notif_to_dict2(notif))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Generate event notification
        if path == "/api/stellar/notifications/event":
            from narrative_agentic.stellar_outreach.notifications import (
                generate_event_notification as _gen_event,
                notification_to_dict as _notif_to_dict3,
            )

            player_id = data.get('player_id', '')
            event_type = data.get('event_type', '')
            event_data = data.get('event_data')

            if not player_id:
                self._send_error("player_id is required", 400)
                return
            if not event_type:
                self._send_error("event_type is required", 400)
                return

            try:
                notif = _gen_event(player_id, event_type, event_data)
                if notif:
                    self._send_json(_notif_to_dict3(notif))
                else:
                    self._send_json({
                        "blocked": True,
                        "reason": "notification blocked by scheduling rules",
                    })
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Crew Diplomacy (generate) (TASK-008)
        if path == "/api/stellar/mini-game/diplomacy":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                generate_diplomacy_scenario as _gen_dp,
                diplomacy_scenario_to_dict as _dp_to_dict,
            )
            try:
                player_id = data.get('player_id', 'default')
                npc_id = data.get('npc_id')
                cosmic_status = data.get('cosmic_status', 'NEUTRAL')
                diff = data.get('difficulty')
                scenario = _gen_dp(player_id=player_id, npc_id=npc_id,
                                   cosmic_status=cosmic_status, difficulty=diff)
                self._send_json(_dp_to_dict(scenario))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Crew Diplomacy (score) (TASK-008)
        if path == "/api/stellar/mini-game/diplomacy/score":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                score_diplomacy as _score_dp,
                diplomacy_result_to_dict as _dpr_to_dict,
            )
            try:
                scenario_id = data.get('scenario_id', '')
                choice_id = data.get('choice_id', '')
                player_id = data.get('player_id', 'default')
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_dp(scenario_id, choice_id, player_id, time_taken, cosmic_buff)
                self._send_json(_dpr_to_dict(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Signal Decode (generate) (TASK-008)
        if path == "/api/stellar/mini-game/signal-decode":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                generate_signal_puzzle as _gen_sd,
                signal_puzzle_to_dict as _sp_to_dict,
            )
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                player_id = data.get('player_id', 'default')
                puzzle = _gen_sd(difficulty=diff, module_level=mlvl, player_id=player_id)
                self._send_json(_sp_to_dict(puzzle))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Signal Decode (score) (TASK-008)
        if path == "/api/stellar/mini-game/signal-decode/score":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                score_signal_decode as _score_sd,
                signal_result_to_dict as _sr_to_dict,
            )
            try:
                puzzle_id = data.get('puzzle_id', '')
                player_answer = data.get('player_answer', '')
                player_id = data.get('player_id', 'default')
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_sd(puzzle_id, player_answer, player_id, time_taken, cosmic_buff)
                self._send_json(_sr_to_dict(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Resource Harvest (generate) (TASK-008)
        if path == "/api/stellar/mini-game/harvest":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                generate_harvest_board as _gen_hb,
                harvest_board_to_dict as _hb_to_dict,
            )
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                board = _gen_hb(difficulty=diff, module_level=mlvl, cosmic_buff=cosmic_buff)
                self._send_json(_hb_to_dict(board))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Resource Harvest (score) (TASK-008)
        if path == "/api/stellar/mini-game/harvest/score":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                score_harvest as _score_hv,
                harvest_result_to_dict as _hr_to_dict,
            )
            try:
                board_id = data.get('board_id', '')
                merges = data.get('merges', [])
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_hv(board_id, merges, time_taken, cosmic_buff)
                self._send_json(_hr_to_dict(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Sky Scanner (generate) (TASK-008)
        if path == "/api/stellar/mini-game/sky-scanner":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                generate_sky_scanner_session as _gen_ss,
                sky_scanner_session_to_dict as _ss_to_dict,
            )
            try:
                diff = data.get('difficulty')
                mlvl = data.get('module_level', 1)
                event_active = data.get('event_active', False)
                session = _gen_ss(difficulty=diff, module_level=mlvl, event_active=event_active)
                self._send_json(_ss_to_dict(session))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Mini-Game — Sky Scanner (score) (TASK-008)
        if path == "/api/stellar/mini-game/sky-scanner/score":
            from narrative_agentic.stellar_outreach.mini_games_phase2 import (
                score_sky_scanner as _score_ss,
                sky_scanner_result_to_dict as _ssr_to_dict,
            )
            try:
                session_id = data.get('session_id', '')
                identified = data.get('identified', [])
                time_taken = float(data.get('time_taken', 0))
                cosmic_buff = float(data.get('cosmic_buff', 0.0))
                result = _score_ss(session_id, identified, time_taken, cosmic_buff)
                self._send_json(_ssr_to_dict(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Send friend request (TASK-010)
        if path == "/api/stellar/friends/request":
            from narrative_agentic.stellar_outreach.friends import send_friend_request as _send_freq
            try:
                from_id = data.get('from_id', '')
                to_id = data.get('to_id', '')
                message = data.get('message', '')
                if not from_id or not to_id:
                    self._send_error("from_id and to_id are required", 400)
                    return
                self._send_json(_send_freq(from_id, to_id, message))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Respond to friend request (TASK-010)
        if path == "/api/stellar/friends/respond":
            from narrative_agentic.stellar_outreach.friends import respond_to_request as _resp_freq
            try:
                player_id = data.get('player_id', '')
                from_id = data.get('from_id', '')
                accept = data.get('accept', False)
                if not player_id or not from_id:
                    self._send_error("player_id and from_id are required", 400)
                    return
                self._send_json(_resp_freq(player_id, from_id, accept))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Remove friend (TASK-010)
        if path == "/api/stellar/friends/remove":
            from narrative_agentic.stellar_outreach.friends import remove_friend as _rem_friend
            try:
                player_id = data.get('player_id', '')
                friend_id = data.get('friend_id', '')
                if not player_id or not friend_id:
                    self._send_error("player_id and friend_id are required", 400)
                    return
                self._send_json(_rem_friend(player_id, friend_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Block player (TASK-010)
        if path == "/api/stellar/friends/block":
            from narrative_agentic.stellar_outreach.friends import block_player as _block_p
            try:
                player_id = data.get('player_id', '')
                target_id = data.get('target_id', '')
                if not player_id or not target_id:
                    self._send_error("player_id and target_id are required", 400)
                    return
                self._send_json(_block_p(player_id, target_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Calculate compatibility (TASK-010)
        if path == "/api/stellar/compatibility":
            from datetime import date as _date, time as _time
            from narrative_agentic.stellar_outreach.birth_chart import (
                BirthChartInput,
                calculate_birth_chart,
            )
            from narrative_agentic.stellar_outreach.friends import (
                calculate_compatibility as _calc_compat,
                synastry_result_to_dict as _syn_to_dict,
            )
            try:
                # Requires birth data for both players
                player_a = data.get('player_a', {})
                player_b = data.get('player_b', {})

                profiles = []
                ids = []
                for label, pdata in [("player_a", player_a), ("player_b", player_b)]:
                    bd_str = pdata.get('birth_date', '')
                    if not bd_str:
                        self._send_error(f"{label}.birth_date is required", 400)
                        return
                    lat = pdata.get('latitude')
                    lon = pdata.get('longitude')
                    if lat is None or lon is None:
                        self._send_error(f"{label}.latitude and .longitude are required", 400)
                        return
                    bd = _date.fromisoformat(bd_str)
                    bt = None
                    bt_str = pdata.get('birth_time')
                    if bt_str:
                        parts = bt_str.split(':')
                        bt = _time(int(parts[0]), int(parts[1]))
                    inp = BirthChartInput(birth_date=bd, latitude=float(lat),
                                          longitude=float(lon), birth_time=bt)
                    profiles.append(calculate_birth_chart(inp))
                    ids.append(pdata.get('player_id', label))

                result = _calc_compat(profiles[0], profiles[1], ids[0], ids[1])
                self._send_json(_syn_to_dict(result))
            except ValueError as e:
                self._send_error(str(e), 400)
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Send gift (TASK-010)
        if path == "/api/stellar/friends/gift":
            from narrative_agentic.stellar_outreach.friends import send_gift as _send_gift
            try:
                player_id = data.get('player_id', '')
                friend_id = data.get('friend_id', '')
                resource_type = data.get('resource_type', '')
                amount = int(data.get('amount', 0))
                if not player_id or not friend_id or not resource_type:
                    self._send_error("player_id, friend_id, and resource_type are required", 400)
                    return
                self._send_json(_send_gift(player_id, friend_id, resource_type, amount))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Streak check-in (TASK-012)
        if path == "/api/stellar/streak/checkin":
            from narrative_agentic.stellar_outreach.streaks import checkin as _checkin
            try:
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(_checkin(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Purchase freeze (TASK-012)
        if path == "/api/stellar/streak/freeze":
            from narrative_agentic.stellar_outreach.streaks import purchase_freeze as _buy_freeze
            try:
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(_buy_freeze(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Claim streak reward (TASK-012)
        if path == "/api/stellar/streak/claim":
            from narrative_agentic.stellar_outreach.streaks import claim_reward as _claim_sr
            try:
                player_id = data.get('player_id', '')
                milestone_days = int(data.get('milestone_days', 0))
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not milestone_days:
                    self._send_error("milestone_days is required", 400)
                    return
                self._send_json(_claim_sr(player_id, milestone_days))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: NPC interact (TASK-009)
        if path == "/api/stellar/npc/interact":
            from narrative_agentic.stellar_outreach.npc_crew import interact_with_npc
            try:
                player_id = data.get('player_id', '')
                npc_id = data.get('npc_id', '')
                cosmic_status = data.get('cosmic_status', 'NEUTRAL')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not npc_id:
                    self._send_error("npc_id is required", 400)
                    return
                self._send_json(interact_with_npc(player_id, npc_id, cosmic_status))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: NPC gift (TASK-009)
        if path == "/api/stellar/npc/gift":
            from narrative_agentic.stellar_outreach.npc_crew import gift_npc
            try:
                player_id = data.get('player_id', '')
                npc_id = data.get('npc_id', '')
                resource = data.get('resource', '')
                amount = int(data.get('amount', 0))
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not npc_id:
                    self._send_error("npc_id is required", 400)
                    return
                if not resource:
                    self._send_error("resource is required", 400)
                    return
                self._send_json(gift_npc(player_id, npc_id, resource, amount))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild create (TASK-011)
        if path == "/api/stellar/guild/create":
            from narrative_agentic.stellar_outreach.guilds import create_guild
            try:
                player_id = data.get('player_id', '')
                guild_name = data.get('guild_name', '')
                sun_sign = data.get('sun_sign', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not guild_name:
                    self._send_error("guild_name is required", 400)
                    return
                self._send_json(create_guild(player_id, guild_name, sun_sign))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild join (TASK-011)
        if path == "/api/stellar/guild/join":
            from narrative_agentic.stellar_outreach.guilds import join_guild
            try:
                player_id = data.get('player_id', '')
                invite_code = data.get('invite_code', '')
                sun_sign = data.get('sun_sign', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not invite_code:
                    self._send_error("invite_code is required", 400)
                    return
                self._send_json(join_guild(player_id, invite_code, sun_sign))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild leave (TASK-011)
        if path == "/api/stellar/guild/leave":
            from narrative_agentic.stellar_outreach.guilds import leave_guild
            try:
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(leave_guild(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild invite (TASK-011)
        if path == "/api/stellar/guild/invite":
            from narrative_agentic.stellar_outreach.guilds import generate_invite
            try:
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(generate_invite(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild contribute (TASK-011)
        if path == "/api/stellar/guild/contribute":
            from narrative_agentic.stellar_outreach.guilds import contribute_resources
            try:
                player_id = data.get('player_id', '')
                resource = data.get('resource', '')
                amount = int(data.get('amount', 0))
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not resource:
                    self._send_error("resource is required", 400)
                    return
                self._send_json(contribute_resources(player_id, resource, amount))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Guild chat (TASK-011)
        if path == "/api/stellar/guild/chat":
            from narrative_agentic.stellar_outreach.guilds import send_chat_message
            try:
                player_id = data.get('player_id', '')
                message = data.get('message', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not message:
                    self._send_error("message is required", 400)
                    return
                self._send_json(send_chat_message(player_id, message))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Atlas discover (TASK-013)
        if path == "/api/stellar/atlas/discover":
            from narrative_agentic.stellar_outreach.star_atlas import discover_object
            try:
                player_id = data.get('player_id', '')
                object_id = data.get('object_id', '')
                source = data.get('source', 'manual')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not object_id:
                    self._send_error("object_id is required", 400)
                    return
                self._send_json(discover_object(player_id, object_id, source))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Apply skin (TASK-014)
        if path == "/api/stellar/customization/skin":
            from narrative_agentic.stellar_outreach.station_customization import apply_skin
            try:
                player_id = data.get('player_id', '')
                skin_id = data.get('skin_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not skin_id:
                    self._send_error("skin_id is required", 400)
                    return
                self._send_json(apply_skin(player_id, skin_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Unlock decoration (TASK-014)
        if path == "/api/stellar/customization/decoration/unlock":
            from narrative_agentic.stellar_outreach.station_customization import unlock_decoration
            try:
                player_id = data.get('player_id', '')
                decoration_id = data.get('decoration_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not decoration_id:
                    self._send_error("decoration_id is required", 400)
                    return
                self._send_json(unlock_decoration(player_id, decoration_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Apply decoration (TASK-014)
        if path == "/api/stellar/customization/decoration/apply":
            from narrative_agentic.stellar_outreach.station_customization import apply_decoration
            try:
                player_id = data.get('player_id', '')
                decoration_id = data.get('decoration_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not decoration_id:
                    self._send_error("decoration_id is required", 400)
                    return
                self._send_json(apply_decoration(player_id, decoration_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Remove decoration (TASK-014)
        if path == "/api/stellar/customization/decoration/remove":
            from narrative_agentic.stellar_outreach.station_customization import remove_decoration
            try:
                player_id = data.get('player_id', '')
                slot = data.get('slot', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not slot:
                    self._send_error("slot is required", 400)
                    return
                self._send_json(remove_decoration(player_id, slot))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Purchase item (TASK-015)
        if path == "/api/stellar/store/purchase":
            from narrative_agentic.stellar_outreach.cosmetic_store import purchase_item
            try:
                player_id = data.get('player_id', '')
                item_id = data.get('item_id', '')
                currency = data.get('currency', 'gems')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not item_id:
                    self._send_error("item_id is required", 400)
                    return
                self._send_json(purchase_item(player_id, item_id, currency))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Verify IAP receipt (TASK-015)
        if path == "/api/stellar/store/iap/verify":
            from narrative_agentic.stellar_outreach.cosmetic_store import verify_iap_receipt
            try:
                player_id = data.get('player_id', '')
                receipt_data = data.get('receipt_data', '')
                store = data.get('store', 'apple')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not receipt_data:
                    self._send_error("receipt_data is required", 400)
                    return
                self._send_json(verify_iap_receipt(player_id, receipt_data, store))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Gift store item (TASK-015)
        if path == "/api/stellar/store/gift":
            from narrative_agentic.stellar_outreach.cosmetic_store import gift_store_item
            try:
                sender_id = data.get('sender_id', '')
                recipient_id = data.get('recipient_id', '')
                item_id = data.get('item_id', '')
                currency = data.get('currency', 'gems')
                if not sender_id:
                    self._send_error("sender_id is required", 400)
                    return
                if not recipient_id:
                    self._send_error("recipient_id is required", 400)
                    return
                if not item_id:
                    self._send_error("item_id is required", 400)
                    return
                self._send_json(gift_store_item(sender_id, recipient_id, item_id, currency))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Subscribe (TASK-016)
        if path == "/api/stellar/pass/subscribe":
            from narrative_agentic.stellar_outreach.cosmic_pass import subscribe as pass_subscribe
            try:
                player_id = data.get('player_id', '')
                product_id = data.get('product_id', '')
                receipt_data = data.get('receipt_data', '')
                store = data.get('store', 'apple')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not product_id:
                    self._send_error("product_id is required", 400)
                    return
                if not receipt_data:
                    self._send_error("receipt_data is required", 400)
                    return
                self._send_json(pass_subscribe(player_id, product_id, receipt_data, store))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Verify renewal receipt (TASK-016)
        if path == "/api/stellar/pass/verify":
            from narrative_agentic.stellar_outreach.cosmic_pass import verify_subscription_receipt
            try:
                player_id = data.get('player_id', '')
                product_id = data.get('product_id', '')
                receipt_data = data.get('receipt_data', '')
                store = data.get('store', 'apple')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not product_id:
                    self._send_error("product_id is required", 400)
                    return
                if not receipt_data:
                    self._send_error("receipt_data is required", 400)
                    return
                self._send_json(verify_subscription_receipt(player_id, product_id, receipt_data, store))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Cancel subscription (TASK-016)
        if path == "/api/stellar/pass/cancel":
            from narrative_agentic.stellar_outreach.cosmic_pass import cancel_subscription
            try:
                player_id = data.get('player_id', '')
                product_id = data.get('product_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not product_id:
                    self._send_error("product_id is required", 400)
                    return
                self._send_json(cancel_subscription(player_id, product_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Claim tier reward (TASK-016)
        if path == "/api/stellar/pass/claim":
            from narrative_agentic.stellar_outreach.cosmic_pass import claim_tier_reward
            try:
                player_id = data.get('player_id', '')
                tier = data.get('tier', 0)
                track = data.get('track', 'free')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not tier:
                    self._send_error("tier is required", 400)
                    return
                self._send_json(claim_tier_reward(player_id, int(tier), track))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Earn season XP (TASK-016)
        if path == "/api/stellar/pass/earn-xp":
            from narrative_agentic.stellar_outreach.cosmic_pass import earn_season_xp
            try:
                player_id = data.get('player_id', '')
                source = data.get('source', '')
                amount = data.get('amount', None)
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not source:
                    self._send_error("source is required", 400)
                    return
                self._send_json(earn_season_xp(player_id, source, amount))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Claim monthly cosmetic (TASK-016)
        if path == "/api/stellar/pass/monthly-cosmetic":
            from narrative_agentic.stellar_outreach.cosmic_pass import claim_monthly_cosmetic
            try:
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(claim_monthly_cosmetic(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Setup endpoint
        if path == "/api/setup":
            try:
                openai_key = data.get('openai_key', '')
                gemini_key = data.get('gemini_key', '')
                
                if openai_key or gemini_key:
                    from narrative_agentic import configure_apis
                    configure_apis(
                        openai_key=openai_key or None,
                        gemini_key=gemini_key or None
                    )
                else:
                    # Use default keys
                    auto_configure_with_defaults()
                
                self._send_json({"status": "configured"})
            except Exception as e:
                self._send_error(str(e))
            return
        
        # Stellar Outreach: Watch rewarded ad (TASK-017)
        if path == "/api/stellar/ads/watch":
            try:
                from narrative_agentic.stellar_outreach.rewarded_ads import watch_rewarded_ad
                player_id = data.get('player_id', '')
                placement = data.get('placement', '')
                ad_network = data.get('ad_network', 'stub')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                if not placement:
                    self._send_error("placement is required", 400)
                    return
                self._send_json(watch_rewarded_ad(player_id, placement, ad_network))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Start AR session
        if path == "/api/stellar/sky/session":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import start_ar_session
                player_id = data.get('player_id', '')
                lat = float(data.get('lat', 0))
                lng = float(data.get('lng', 0))
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(start_ar_session(player_id, lat, lng))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Identify object in AR session
        if path == "/api/stellar/sky/session/identify":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import identify_object
                player_id = data.get('player_id', '')
                session_id = data.get('session_id', '')
                object_id = data.get('object_id', '')
                if not player_id or not session_id or not object_id:
                    self._send_error("player_id, session_id, and object_id are required", 400)
                    return
                self._send_json(identify_object(player_id, session_id, object_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Stellar Outreach: Complete AR session
        if path == "/api/stellar/sky/session/complete":
            try:
                from narrative_agentic.stellar_outreach.ar_sky_scanner import complete_ar_session
                player_id = data.get('player_id', '')
                session_id = data.get('session_id', '')
                if not player_id or not session_id:
                    self._send_error("player_id and session_id are required", 400)
                    return
                self._send_json(complete_ar_session(player_id, session_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # ─── Auth: register new player ───────────────────────────
        if path == "/api/auth/register":
            try:
                from narrative_agentic.stellar_outreach.auth import register_player
                self._send_json(register_player())
            except Exception as e:
                self._send_error(str(e))
            return

        # ─── Auth: complete onboarding ───────────────────────────
        if path == "/api/auth/complete":
            try:
                from narrative_agentic.stellar_outreach.auth import complete_onboarding
                player_id = data.get('player_id', '')
                if not player_id:
                    self._send_error("player_id is required", 400)
                    return
                self._send_json(complete_onboarding(player_id))
            except Exception as e:
                self._send_error(str(e))
            return

        # Analytics event ingestion
        if path == "/api/analytics/events":
            try:
                player_id = data.get("player_id", "anonymous")
                events = data.get("events", [])
                import json as _json
                import os as _os
                log_dir = _os.path.expanduser("~/.nexus_station/analytics")
                _os.makedirs(log_dir, exist_ok=True)
                log_path = _os.path.join(log_dir, f"{player_id}.jsonl")
                with open(log_path, "a") as f:
                    for ev in events:
                        f.write(_json.dumps(ev) + "\n")
                self._send_json({"ok": True, "ingested": len(events)})
            except Exception as e:
                self._send_error(str(e))
            return

        # Default - 404
        self._send_error("Not found", 404)

    def log_message(self, format, *args):
        """Override to customize logging."""
        print("[SERVER] {} - {}".format(self.address_string(), format % args))


def run_server(port: int = 8080):
    """Run the API server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    
    print()
    print("==============================================================")
    print()
    print("   N E X U S   S T A T I O N                                  ")
    print("   API Server                                                 ")
    print("                                                              ")
    print("   Model Versions:                                            ")
    print("   - OpenAI: gpt-5.2-codex-mini                               ")
    print("   - Gemini: gemini-3-flash-preview                           ")
    print()
    print("==============================================================")
    print("   Server running at: http://localhost:{}".format(port))
    print()
    print("   Endpoints:")
    print("     GET  /api/status    - System status")
    print("     GET  /api/crew      - Crew information")
    print("     GET  /api/precedents - Recent precedents")
    print("     POST /api/chat      - Send message to agent")
    print("     POST /api/summary   - Generate session summary")
    print("     POST /api/actions/confirm - Confirm pending action (Article V)")
    print("     POST /api/setup     - Configure APIs")
    print("     GET  /api/stellar/discovery-card - Today's Discovery Card")
    print("     GET  /api/stellar/collection     - Card collection stats")
    print("     POST /api/stellar/birth-chart    - Calculate natal birth chart")
    print("     GET  /api/stellar/sky-today      - Today's transit sky (universal)")
    print("     POST /api/stellar/daily-briefing - Personalized cosmic briefing")
    print("     POST /api/stellar/briefing       - Full daily cosmic briefing")
    print("     POST /api/stellar/station        - Create new station")
    print("     GET  /api/stellar/station        - Get station state")
    print("     POST /api/stellar/station/collect - Collect resources")
    print("     POST /api/stellar/station/upgrade - Upgrade module")
    print("     POST /api/stellar/mini-game/star-pattern       - Generate star puzzle")
    print("     POST /api/stellar/mini-game/star-pattern/score - Score star puzzle")
    print("     POST /api/stellar/mini-game/repair             - Generate repair puzzle")
    print("     POST /api/stellar/mini-game/repair/score       - Score repair puzzle")
    print("     POST /api/stellar/mini-game/asteroid           - Generate asteroid scenario")
    print("     POST /api/stellar/mini-game/asteroid/score     - Score deflection attempt")
    print("     GET  /api/stellar/daily-mission                - Get daily mission")
    print("     POST /api/stellar/notifications/morning        - Generate morning briefing")
    print("     POST /api/stellar/notifications/event          - Generate event notification")
    print("     GET  /api/stellar/notifications/history        - Notification history")
    print("     GET  /api/stellar/notifications/preferences    - Get notification prefs")
    print("     PUT  /api/stellar/notifications/preferences    - Update notification prefs")
    print("     --- Phase 2: Mini-Games (TASK-008) ---")
    print("     POST /api/stellar/mini-game/diplomacy          - Generate diplomacy scenario")
    print("     POST /api/stellar/mini-game/diplomacy/score    - Score diplomacy choice")
    print("     POST /api/stellar/mini-game/signal-decode      - Generate signal puzzle")
    print("     POST /api/stellar/mini-game/signal-decode/score- Score signal decode")
    print("     POST /api/stellar/mini-game/harvest            - Generate harvest board")
    print("     POST /api/stellar/mini-game/harvest/score      - Score harvest game")
    print("     POST /api/stellar/mini-game/sky-scanner        - Generate sky scanner session")
    print("     POST /api/stellar/mini-game/sky-scanner/score  - Score sky scanner")
    print("     --- Phase 2: Friends & Compatibility (TASK-010) ---")
    print("     GET  /api/stellar/friends                      - List friends")
    print("     GET  /api/stellar/friends/requests             - Pending requests")
    print("     POST /api/stellar/friends/request              - Send friend request")
    print("     POST /api/stellar/friends/respond              - Accept/reject request")
    print("     POST /api/stellar/friends/remove               - Remove friend")
    print("     POST /api/stellar/friends/block                - Block player")
    print("     POST /api/stellar/compatibility                - Calculate synastry")
    print("     POST /api/stellar/friends/gift                 - Send resource gift")
    print("     --- Phase 2: Streaks (TASK-012) ---")
    print("     GET  /api/stellar/streak                       - Current streak data")
    print("     GET  /api/stellar/streak/rewards               - Streak rewards")
    print("     POST /api/stellar/streak/checkin               - Record check-in")
    print("     POST /api/stellar/streak/freeze                - Purchase freeze")
    print("     POST /api/stellar/streak/claim                 - Claim streak reward")
    print("     --- Phase 2: NPC Crew (TASK-009) ---")
    print("     GET  /api/stellar/npc/list                     - All NPCs with relationship status")
    print("     GET  /api/stellar/npc/detail                   - Single NPC detail")
    print("     POST /api/stellar/npc/interact                 - Daily interaction")
    print("     POST /api/stellar/npc/gift                     - Give resource gift to NPC")
    print("     GET  /api/stellar/npc/perks                    - Active perks from all NPCs")
    print("     --- Phase 2: Guilds (TASK-011) ---")
    print("     POST /api/stellar/guild/create                 - Create new guild")
    print("     GET  /api/stellar/guild                        - Get guild details")
    print("     POST /api/stellar/guild/join                   - Join via invite code")
    print("     POST /api/stellar/guild/leave                  - Leave guild")
    print("     POST /api/stellar/guild/invite                 - Generate invite code")
    print("     POST /api/stellar/guild/contribute             - Contribute resources")
    print("     GET  /api/stellar/guild/challenge              - Weekly challenge status")
    print("     POST /api/stellar/guild/chat                   - Send chat message")
    print("     --- Phase 2: Star Atlas (TASK-013) ---")
    print("     GET  /api/stellar/atlas                        - Full atlas with discovery stats")
    print("     GET  /api/stellar/atlas/category               - Category detail")
    print("     POST /api/stellar/atlas/discover               - Mark object as discovered")
    print("     GET  /api/stellar/atlas/missions               - Mission archive")
    print("     GET  /api/stellar/atlas/passport               - Cosmic passport stamps")
    print("     --- Phase 2: Station Customization (TASK-014) ---")
    print("     GET  /api/stellar/customization                - Full customization state")
    print("     GET  /api/stellar/customization/skins          - Available skins")
    print("     GET  /api/stellar/customization/decorations    - Available decorations")
    print("     GET  /api/stellar/customization/preview        - Preview skin")
    print("     GET  /api/stellar/customization/palette        - Element palette")
    print("     POST /api/stellar/customization/skin           - Apply skin")
    print("     POST /api/stellar/customization/decoration/unlock - Unlock decoration")
    print("     POST /api/stellar/customization/decoration/apply  - Apply decoration")
    print("     POST /api/stellar/customization/decoration/remove - Remove decoration")
    print()
    print("   Cosmetic Store (TASK-015):")
    print("     GET  /api/stellar/store/catalog               - Browse store catalog")
    print("     GET  /api/stellar/store/featured              - Featured items this week")
    print("     GET  /api/stellar/store/wallet                - Player wallet & gems")
    print("     GET  /api/stellar/store/history               - Transaction history")
    print("     GET  /api/stellar/store/packs                 - IAP gem packs")
    print("     GET  /api/stellar/store/summary               - Store summary screen")
    print("     POST /api/stellar/store/purchase              - Purchase item")
    print("     POST /api/stellar/store/iap/verify            - Verify IAP receipt")
    print("     POST /api/stellar/store/gift                  - Gift item to friend")
    print()
    print("   Cosmic Pass & Stellar Premium (TASK-016):")
    print("     GET  /api/stellar/pass/status                 - Subscription status")
    print("     GET  /api/stellar/pass/season                 - Current season info")
    print("     GET  /api/stellar/pass/progress               - Player tier & XP")
    print("     GET  /api/stellar/pass/rewards                - 30 tiers with claim status")
    print("     GET  /api/stellar/pass/benefits               - Active benefits summary")
    print("     GET  /api/stellar/pass/products               - Subscription product list")
    print("     POST /api/stellar/pass/subscribe              - Subscribe with receipt")
    print("     POST /api/stellar/pass/verify                 - Verify renewal receipt")
    print("     POST /api/stellar/pass/cancel                 - Cancel auto-renewal")
    print("     POST /api/stellar/pass/claim                  - Claim tier reward")
    print("     POST /api/stellar/pass/earn-xp                - Award season XP")
    print("     POST /api/stellar/pass/monthly-cosmetic       - Claim monthly cosmetic")
    print()
    print("   AR Sky Scanner (TASK-018):")
    print("     GET  /api/stellar/iss/current                - ISS current position")
    print("     GET  /api/stellar/iss/passes                 - ISS pass predictions")
    print("     GET  /api/stellar/sky/visible                - Visible sky objects")
    print("     GET  /api/stellar/sky/snapshot               - Full sky snapshot")
    print("     GET  /api/stellar/sky/constellation/{id}     - Constellation detail")
    print("     GET  /api/stellar/sky/config                 - Sky scanner config")
    print("     GET  /api/stellar/sky/history                - AR session history")
    print("     POST /api/stellar/sky/session                - Start AR session")
    print("     POST /api/stellar/sky/session/identify       - Identify object")
    print("     POST /api/stellar/sky/session/complete       - Complete AR session")
    print()
    print("   Astronomical Events (TASK-019):")
    print("     GET  /api/stellar/events/active             - Active events now")
    print("     GET  /api/stellar/events/upcoming           - Upcoming events")
    print("     GET  /api/stellar/events/detail/{id}        - Event detail")
    print("     GET  /api/stellar/events/calendar           - Monthly calendar")
    print("     GET  /api/stellar/events/bonuses            - Player event bonuses")
    print("     GET  /api/stellar/events/config             - Event system config")
    print()
    print("   Press Ctrl+C to stop")
    print()
    print("==============================================================")
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
        print("[SERVER] Shutting down...")
        httpd.shutdown()
        print("[SERVER] Goodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NEXUS STATION API Server")
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=8080,
        help='Port to run the server on (default: 8080)'
    )
    
    args = parser.parse_args()
    
    run_server(args.port)
