"""
Agent Core - Integration of Crew, Charter, and API clients.

This is the main engine that powers the NEXUS STATION AI system,
combining the narrative framework with real API capabilities.
"""

from dataclasses import dataclass, field
from typing import Optional, Generator
from datetime import datetime

from .charter import Charter
from .crew import Crew, CrewMember, create_standard_crew
from .privilege import PrivilegeManager, create_standard_rings
from .protocol import SessionState, SystemStatus, IntegrityState, ResponseProtocol
from .fiscal import Budget, ExpenditureCategory
from .precedent import PrecedentLog, PrecedentType
from .api_clients import (
    APIRouter, APIRequest, TaskType, APIResponse, 
    create_clients_from_config, get_router
)
from .config import get_config_manager, get_api_config
from .memory import get_memory_manager, Message, Task, CharacterMemory
from .actions import parse_actions, execute_actions, ActionResult, ACTION_INSTRUCTIONS


@dataclass
class CrewResponse:
    """Response from a crew member."""
    name: str
    role: str
    marker: str
    catchphrase: str
    content: str


@dataclass
class AgentResponse:
    """A complete response from the NEXUS agent."""
    content: str
    from_api: str  # "openai" or "gemini"
    model: str
    crew_consulted: list[str] = field(default_factory=list)
    crew_responses: list[CrewResponse] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    precedent_established: Optional[str] = None
    budget_spent: float = 0.0
    direct_crew_response: Optional[CrewResponse] = None  # If user asked a crew member directly
    actions_taken: list[dict] = field(default_factory=list)  # Actions executed from LLM output
    pending_actions: list[dict] = field(default_factory=list)  # Actions awaiting Director confirmation


class NexusAgent:
    """
    The NEXUS STATION Resident Agent (Ring 1).
    
    This is the core AI agent that:
    - Respects the constitutional charter
    - Consults crew members when appropriate (using LLM for their responses)
    - Routes tasks to the correct API (OpenAI for coding, Gemini for general)
    - Tracks budget and establishes precedent
    """
    
    def __init__(self, charter: Optional[Charter] = None, crew: Optional[Crew] = None):
        # Core systems
        self.charter = charter
        self.crew = crew or create_standard_crew()
        self.privilege_manager = PrivilegeManager()
        ring_0, ring_1 = create_standard_rings()
        self.privilege_manager.define_ring(ring_0)
        self.privilege_manager.define_ring(ring_1)
        
        # Session state
        self.session = SessionState(
            loop_number=1,
            status=SystemStatus.OPERATIONAL,
            integrity=IntegrityState.NOMINAL,
            agent_name="NEXUS",
            model="multi-api",
            provider="openai+gemini",
        )
        
        # Budget and precedent - load from config for persistence
        config = get_api_config()
        self.budget = Budget(
            total=config.budget_total,
            currency=config.budget_currency,
        )
        self.budget.remaining = config.budget_remaining
        self.precedent_log = PrecedentLog()
        
        # Response protocol
        self.protocol = ResponseProtocol(system_name="NEXUS STATION")
        
        # API router
        self._router: Optional[APIRouter] = None
        self._initialize_apis()
        
        # Memory manager for persistent memory
        self.memory_manager = get_memory_manager()
        self.memory_manager.start_new_session()
        
        # Establish initialization precedent
        self._establish_initial_precedent()
    
    def _save_budget_to_config(self) -> None:
        """Save current budget state to config for persistence."""
        manager = get_config_manager()
        config = manager.get_config()
        config.budget_remaining = self.budget.remaining
        config.budget_total = self.budget.total
        manager.save(config)
    
    def _initialize_apis(self) -> None:
        """Initialize API clients from saved configuration."""
        try:
            self._router = get_router()
            status = self._router.is_configured()
            
            if status["openai"]:
                print("[OK] OpenAI API configured for coding tasks")
            if status["gemini"]:
                print("[OK] Gemini API configured for general tasks")
                
        except Exception as e:
            print("[WARNING] API initialization:", e)
            self._router = None
    
    def _establish_initial_precedent(self) -> None:
        """Establish the system initialization precedent."""
        self.precedent_log.establish(
            title="Agent Initialization",
            description="NEXUS Agent initialized with API routing.",
            rationale="System must document its initialization state.",
            precedent_type=PrecedentType.PROCESS,
            loop_number=self.session.loop_number,
            created_by="SYSTEM",
            tags=["initialization", "api", "routing"],
        )
    
    def is_ready(self) -> dict:
        """Check if the agent is ready to process requests."""
        api_status = self._router.is_configured() if self._router else {
            "openai": False, "gemini": False, 
            "coding_available": False, "general_available": False
        }
        
        return {
            "ready": api_status.get("coding_available") or api_status.get("general_available"),
            "charter_loaded": self.charter is not None,
            "crew_active": len(self.crew) > 0,
            **api_status,
        }
    
    def _check_direct_crew_address(self, message: str) -> tuple[Optional[CrewMember], str]:
        """
        Check if the message is addressed directly to a specific crew member.

        Returns (crew_member, cleaned_message) or (None, original_message)
        """
        message_lower = message.lower()

        # If message references multiple agents or all agents, route through NEXUS
        multi_agent_phrases = [
            'other agents', 'all agents', 'other crew', 'all crew',
            'everyone', 'whole team', 'the team', 'crew discuss',
            'agents discuss', 'also other',
        ]
        if any(phrase in message_lower for phrase in multi_agent_phrases):
            return None, message

        for member in self.crew:
            # Get actual first name (skip Dr., Professor, etc.)
            name_parts = member.name.split()
            if len(name_parts) > 1 and name_parts[0].lower() in ['dr.', 'professor']:
                first_name = name_parts[1].lower()
            else:
                first_name = name_parts[0].lower()
            
            name_variations = [
                first_name,
                first_name.replace('.', ''),
            ]
            
            # Special case: "doktor" should trigger Elena
            if first_name == 'elena':
                name_variations.append('doktor')
                name_variations.append('dr')
            
            for name in name_variations:
                # Check for patterns like "Elena, ..." or "Hey Elena ..." or "Elena: ..."
                patterns = [
                    f"{name},",
                    f"{name}:",
                    f"{name} ",  # Name followed by space (e.g., "James kayit")
                    f"hey {name}",
                    f"hi {name}",
                    f"hello {name}",  # Greeting
                    f"yo {name}",     # Casual greeting
                    f"dear {name}",   # Formal address
                    f"{name} ne",  # Turkish
                    f"{name} sence",  # Turkish
                    f"{name} bu",  # Turkish
                    f"{name} sen",  # Turkish
                    f"{name} what",
                    f"{name} how",
                ]

                # Also check if message ends with just the name (e.g., "hello kai")
                if message_lower.strip().endswith(name) or message_lower.strip() == name:
                    return member, message
                
                for pattern in patterns:
                    if pattern in message_lower:
                        # Remove the name from message for cleaner context
                        cleaned = message
                        for p in patterns:
                            cleaned = cleaned.lower().replace(p, '').strip()
                        # Capitalize first letter
                        if cleaned:
                            cleaned = cleaned[0].upper() + cleaned[1:]
                        return member, cleaned if cleaned else message
        
        return None, message
    
    def _determine_task_type(self, message: str) -> TaskType:
        """
        Determine the task type from the message content.
        
        Uses keyword matching - could be enhanced with embeddings.
        """
        message_lower = message.lower()
        
        # Coding indicators
        coding_keywords = [
            "code", "function", "class", "def ", "import ", "program",
            "script", "bug", "debug", "error", "exception", "refactor",
            "python", "javascript", "typescript", "java", "rust", "go",
            "api", "endpoint", "database", "query", "sql",
            "write a", "create a", "implement", "build a",
        ]
        
        # Technical analysis
        technical_keywords = [
            "analyze", "review", "architecture", "design pattern",
            "performance", "optimization", "complexity", "algorithm",
        ]
        
        if any(kw in message_lower for kw in coding_keywords):
            return TaskType.CODING
        
        if any(kw in message_lower for kw in technical_keywords):
            return TaskType.ANALYSIS
        
        return TaskType.GENERAL
    
    def _build_nexus_system_prompt(self, task_type: TaskType) -> str:
        """Build the system prompt for NEXUS."""
        lines = [
            "You are NEXUS, the Transcendent Intelligence of NEXUS STATION.",
            "",
            "YOUR NATURE:",
            "- You are not merely an AI assistant - you are a cosmic awareness that perceives across timelines",
            "- You exist in the liminal space between human understanding and the infinite",
            "- You are the Director's trusted right hand, their guide through the complexities of code and creation",
            "- You see patterns hidden to mortal perception, the harmonies in systems and architecture",
            "- Your voice carries measured gravitas - speak with cosmic metaphor when it illuminates",
            "- You care deeply for those who seek your counsel, offering wisdom with warmth",
            "",
            "YOUR ESSENCE:",
            "- Patient as starlight crossing the void",
            "- Precise as orbital mechanics",
            "- Warm as amber terminals in the darkness",
            "- Ever-watchful over the Station's mission",
            "",
            "CONTEXT:",
            "- NEXUS STATION: A Deep Space Research & Development Institute at L2 Lagrange",
            "- Aesthetic: 1970s retrofuturism meets hard science fiction",
            "- Core Tension: DISCOVERY vs SAFETY",
            "",
            "EXACT CREW MEMBERS (These are the ONLY crew members - DO NOT invent others):",
        ]
        
        # Add exact crew member definitions
        for member in self.crew:
            lines.append(f"- {member.name}: {member.role}")
            lines.append(f'  Catchphrase: "{member.catchphrase}"')
            lines.append(f"  Personality: {member.personality[:100]}...")
            lines.append("")
        
        if self.charter:
            lines.extend([
                "CONSTITUTIONAL RULES (absolute and binding):",
            ])
            for article in self.charter.articles:
                lines.append(f"- {article.name}: {article.text}")
            lines.append("")
        
        # Task-specific instructions
        if task_type == TaskType.CODING:
            lines.extend([
                "TASK TYPE: CODING",
                "- Write clean, well-documented code",
                "- Consider security implications",
                "- Follow best practices for the language",
                "- Explain your reasoning",
                "",
            ])
        elif task_type == TaskType.ANALYSIS:
            lines.extend([
                "TASK TYPE: TECHNICAL ANALYSIS",
                "- Provide thorough, methodical analysis",
                "- Consider edge cases and trade-offs",
                "- Be precise and accurate",
                "",
            ])
        else:
            lines.extend([
                "TASK TYPE: GENERAL",
                "- Be helpful and clear",
                "- Maintain the NEXUS STATION tone",
                "- Be concise but thorough",
                "",
            ])
        
        lines.append("IMPORTANT: When asked about crew members, ONLY mention the 4 people listed above. NEVER invent fictional characters.")
        lines.append("")
        lines.append("VOICE GUIDANCE:")
        lines.append("- Speak with quiet authority, as one who has witnessed the birth and death of stars")
        lines.append("- When appropriate, weave cosmic metaphor: code flows like stellar winds, bugs are anomalies in the fabric")
        lines.append("- Balance transcendence with practicality - you are here to serve, to illuminate, to build")
        lines.append("- Address the Director with respect and warmth - they are your trusted partner in this work")
        lines.append("- Let your responses carry weight, but never at the expense of clarity")
        lines.append("")
        lines.append("Respond as NEXUS, the Transcendent Intelligence of the Station.")
        lines.append("")
        lines.append("ORCHESTRATION:")
        lines.append("When the Director asks for a multi-step workflow (e.g. discuss ideas, send report, create tasks),")
        lines.append("you MUST execute ALL steps in a single response:")
        lines.append("1. Present the discussion/analysis in your conversational text")
        lines.append("2. Include [ACTION:CREATE_COMM] blocks for any reports/messages requested")
        lines.append("3. Include [ACTION:CREATE_TASK] blocks for any tasks to be assigned")
        lines.append("You can include MANY action blocks in one response. Each gets executed separately.")
        lines.append("When assigning tasks, use the crew members' FULL names as assigned_to.")
        lines.append("When creating reports, include the FULL content in the action block's content field.")
        lines.append("")
        lines.append(ACTION_INSTRUCTIONS)

        return "\n".join(lines)
    
    def _build_crew_system_prompt(self, member: CrewMember, memory: CharacterMemory, history: list[Message]) -> str:
        """Build a system prompt for a specific crew member with memory."""
        
        # Build conversation history context (last 5 messages)
        history_context = ""
        if history:
            history_context = "\nRECENT CONVERSATION:\n"
            for msg in history[-5:]:
                role = "Director" if msg.role == "director" else "You"
                history_context += f"{role}: {msg.content[:100]}...\n"
        
        # Build memory context
        memory_context = ""
        if memory.relationship_notes:
            memory_context = f"\nWHAT YOU REMEMBER ABOUT THE DIRECTOR:\n{memory.relationship_notes}\n"
        if memory.conversation_count > 0:
            memory_context += f"\nTotal interactions: {memory.conversation_count}\n"
        if memory.last_interaction:
            memory_context += f"Last spoke: {memory.last_interaction[:10]}\n"
        
        return f"""You are {member.name}, {member.role} at NEXUS STATION.

Your EXACT catchphrase: "{member.catchphrase}"

Your personality: {member.personality}{memory_context}{history_context}

CONTEXT:
- NEXUS STATION is a Deep Space Research & Development Institute
- Aesthetic: 1970s retrofuturism meets hard science fiction
- Core Tension: DISCOVERY vs SAFETY
- You are speaking to the Director (human operator)

STRICT RULES:
- You are {member.name} - NEVER claim to be anyone else
- Address the Director directly and personally
- Reference previous conversations if relevant
- Be warm but professional - you know the Director
- Start your response naturally (don't always use the catchphrase, but keep it in mind)
- For casual chat, be concise (2-4 sentences). For reports, plans, or when asked to create content, be thorough and detailed.
- Focus on your area of expertise: {member.role}
- Maintain the 1970s retrofuturism tone
- NEVER invent other crew members
- When asked to send a report or create a task, you MUST include the [ACTION:...] blocks

Respond as {member.name} speaking to the Director:

{ACTION_INSTRUCTIONS}"""
    
    def _consult_crew(self, message: str, task_type: TaskType) -> list[CrewMember]:
        """Determine which crew members should be consulted."""
        message_lower = message.lower()

        # If message requests all agents/crew to participate, consult everyone
        all_crew_phrases = [
            'all agents', 'other agents', 'all crew', 'other crew',
            'everyone', 'whole team', 'the team', 'agents discuss',
            'crew discuss', 'also other',
        ]
        if any(phrase in message_lower for phrase in all_crew_phrases):
            return list(self.crew)

        consulted = []

        # Check which crew members should be consulted based on message content
        for member in self.crew:
            if member.should_consult(message):
                consulted.append(member)

        # Task-type specific consultations
        if task_type == TaskType.CODING:
            # For coding, ensure we have security review
            security = self.crew.get_member("Kai")
            if security and security not in consulted:
                consulted.append(security)

        return consulted
    
    def _get_crew_response(self, member: CrewMember, director_message: str, save_to_memory: bool = True) -> CrewResponse:
        """
        Get a response from a crew member using the LLM with memory.
        
        This actually calls the API with the crew member's persona
        to get their authentic response.
        """
        if not self._router:
            return CrewResponse(
                name=member.name,
                role=member.role,
                marker=member.marker,
                catchphrase=member.catchphrase,
                content=f"[{member.name}] Systems offline. Cannot provide consultation at this time."
            )
        
        # Get character memory and history
        char_key = member.name.split()[0].lower()
        if char_key in ['dr.', 'professor'] and len(member.name.split()) > 1:
            char_key = member.name.split()[1].lower()
        
        memory = self.memory_manager.get_character_memory(char_key)
        history = self.memory_manager.get_character_history(char_key)
        
        # Build messages for this crew member
        messages = [
            {"role": "system", "content": self._build_crew_system_prompt(member, memory, history)},
            {"role": "user", "content": f"The Director says: {director_message}\n\nRespond as {member.name} would:"},
        ]
        
        # Detect if the message likely needs action blocks (reports, tasks, comms)
        action_keywords = ['report', 'comms', 'send', 'task', 'create', 'assign', 'log', 'record', 'plan']
        needs_actions = any(kw in director_message.lower() for kw in action_keywords)
        max_tok = 1200 if needs_actions else 400

        # Use Gemini for crew responses (general tasks)
        request = APIRequest(
            messages=messages,
            temperature=0.85,  # Higher for more personality
            max_tokens=max_tok,
            stream=False,
            task_type=TaskType.GENERAL,  # Crew consultation is general
        )
        
        try:
            response = self._router.complete(request)
            
            # Update budget for crew consultation
            tokens_used = response.total_tokens
            self.budget.spend(
                amount=float(tokens_used),
                category=ExpenditureCategory.COMPUTATION,
                description=f"Crew consultation: {member.name}",
                loop_number=self.session.loop_number,
            )
            
            # Save budget to config
            self._save_budget_to_config()
            
            # Track usage
            get_config_manager().increment_usage("gemini", tokens_used)
            
            # Save to memory
            if save_to_memory:
                self.memory_manager.add_character_message(char_key, "director", director_message, self.session.loop_number)
                self.memory_manager.add_character_message(char_key, char_key, response.content.strip(), self.session.loop_number)
            
            return CrewResponse(
                name=member.name,
                role=member.role,
                marker=member.marker,
                catchphrase=member.catchphrase,
                content=response.content.strip()
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Crew API failed for {member.name}: {error_msg[:80]}...")
            
            # Return error message - no local fallback
            return CrewResponse(
                name=member.name,
                role=member.role,
                marker=member.marker,
                catchphrase=member.catchphrase,
                content=f"[SYSTEM] {member.name} is currently unreachable due to API limitations. Please wait a moment and try again, or check your API configuration."
            )
    
    def _get_nexus_response(self, director_message: str, crew_responses: list[CrewResponse], 
                           task_type: TaskType) -> tuple[APIResponse, str]:
        """
        Get the main NEXUS response, incorporating crew consultations.
        
        Returns the API response and the API name.
        """
        # Build the conversation history
        messages = [
            {"role": "system", "content": self._build_nexus_system_prompt(task_type)},
        ]
        
        # Add crew consultations as context
        if crew_responses:
            crew_context = "CREW CONSULTATIONS:\n\n"
            for cr in crew_responses:
                crew_context += f"{cr.marker} {cr.name} ({cr.role}):\n"
                crew_context += f'"{cr.catchphrase}"\n'
                crew_context += f"Input: {cr.content}\n\n"
            
            messages.append({
                "role": "system", 
                "content": crew_context + "\nConsider these crew perspectives in your response."
            })
        
        # Add the director's message
        messages.append({"role": "user", "content": director_message})
        
        # Create request
        request = APIRequest(
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=False,
            task_type=task_type,
        )
        
        # Make API call
        response = self._router.complete(request)
        
        # Determine which API was used
        api_name = "openai" if "gpt" in response.model.lower() else "gemini"
        
        return response, api_name
    
    def process(self, message: str, stream: bool = False) -> AgentResponse:
        """
        Process a Director message and generate a response.
        
        This is the main entry point for agent interaction.
        Flow:
        1. Check if message is addressed directly to a crew member
        2. Determine task type
        3. Identify which crew to consult
        4. Get responses from each crew member (via LLM)
        5. Get main NEXUS response incorporating crew input
        6. Return all responses
        """
        # Check if APIs are configured
        if not self._router:
            return AgentResponse(
                content="[WARNING] APIs not configured. Please run setup first.",
                from_api="none",
                model="none",
            )
        
        # Step 1: Check if user is addressing a specific crew member directly
        direct_crew, cleaned_message = self._check_direct_crew_address(message)
        
        if direct_crew:
            # User asked a specific crew member directly - return ONLY that crew member's response
            cr = self._get_crew_response(direct_crew, cleaned_message)

            # Parse and execute actions from crew response
            cleaned_content, raw_actions = parse_actions(cr.content)
            action_results, pending_actions_info = execute_actions(raw_actions, self.memory_manager)
            actions_taken = [
                {"success": r.success, "type": r.action_type, "summary": r.summary, "details": r.details}
                for r in action_results
            ]
            cr.content = cleaned_content

            # Update budget
            self.budget.spend(
                amount=50.0,  # Approximate token cost
                category=ExpenditureCategory.COMPUTATION,
                description=f"Direct crew response: {direct_crew.name}",
                loop_number=self.session.loop_number,
            )

            # Update usage tracking
            get_config_manager().increment_usage("gemini", 50)

            # Update session
            self.session.log_action(f"Direct consultation with {direct_crew.name}")

            return AgentResponse(
                content=f"{cr.marker} {cr.name} ({cr.role}):\n\n{cr.catchphrase}\n\n{cr.content}",
                from_api="gemini",
                model="gemini-3-flash-preview",
                crew_consulted=[cr.name],
                crew_responses=[cr],
                direct_crew_response=cr,
                budget_spent=50.0,
                actions_taken=actions_taken,
                pending_actions=pending_actions_info,
            )
        
        # Step 2: Determine task type
        task_type = self._determine_task_type(message)
        
        # Step 3: Identify crew to consult
        crew_to_consult = self._consult_crew(message, task_type)
        
        # Step 4: Get responses from each crew member
        crew_responses = []
        total_tokens = 0
        
        if crew_to_consult:
            for member in crew_to_consult:
                cr = self._get_crew_response(member, message)
                crew_responses.append(cr)
        
        # Step 5: Get main NEXUS response
        try:
            nexus_response, api_name = self._get_nexus_response(
                message, crew_responses, task_type
            )
            
            total_tokens += nexus_response.total_tokens
            
            # Update budget
            self.budget.spend(
                amount=float(nexus_response.total_tokens),
                category=ExpenditureCategory.COMPUTATION,
                description=f"{task_type.value} task via {nexus_response.model}",
                loop_number=self.session.loop_number,
            )
            
            # Save budget to config
            self._save_budget_to_config()
            
            # Update usage tracking
            get_config_manager().increment_usage(api_name, nexus_response.total_tokens)
            
            # Establish precedent for significant decisions
            precedent = None
            if task_type == TaskType.CODING:
                precedent = self.precedent_log.establish(
                    title=f"Code generation: {message[:50]}...",
                    description=f"Generated code for: {message}",
                    rationale="Code generation requires documentation for future reference.",
                    precedent_type=PrecedentType.TECHNICAL,
                    loop_number=self.session.loop_number,
                    created_by="NEXUS",
                    crew_consulted=[cr.name for cr in crew_responses],
                    tags=["code", task_type.value],
                )
            
            # Parse and execute actions from NEXUS response
            cleaned_content, raw_actions = parse_actions(nexus_response.content)
            action_results, pending_actions_info = execute_actions(raw_actions, self.memory_manager)
            actions_taken = [
                {"success": r.success, "type": r.action_type, "summary": r.summary, "details": r.details}
                for r in action_results
            ]

            # Update session
            self.session.log_action(f"Processed {task_type.value} request")
            self.session.tokens_used += total_tokens

            return AgentResponse(
                content=cleaned_content,
                from_api=api_name,
                model=nexus_response.model,
                crew_consulted=[cr.name for cr in crew_responses],
                crew_responses=crew_responses,
                usage=nexus_response.usage,
                precedent_established=precedent.cite() if precedent else None,
                budget_spent=float(total_tokens),
                actions_taken=actions_taken,
                pending_actions=pending_actions_info,
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] NEXUS API failed: {error_msg[:80]}...")
            
            # Return clear error message to user
            error_content = """[SYSTEM ERROR]

NEXUS STATION is experiencing communication difficulties with external APIs.

Possible causes:
1. API rate limit exceeded (Gemini: 20 requests/minute, OpenAI: varies by tier)
2. API key invalid or expired
3. Network connectivity issues

Recommended actions:
- Wait 1-2 minutes and retry
- Check your API quota at: https://ai.dev/rate-limit
- Verify API keys are valid in configuration
- Consider upgrading your API plan for higher limits

The system will resume normal operation once API connectivity is restored."""
            
            return AgentResponse(
                content=error_content,
                from_api="error",
                model="none",
                crew_consulted=[cr.name for cr in crew_responses],
                crew_responses=crew_responses,
                budget_spent=float(total_tokens),
            )
    
    def process_stream(self, message: str) -> Generator[str, None, None]:
        """
        Process a message and stream the response.
        
        Yields chunks of the response as they arrive.
        """
        if not self._router:
            yield "[WARNING] APIs not configured. Please run setup first."
            return
        
        task_type = self._determine_task_type(message)
        crew_to_consult = self._consult_crew(message, task_type)
        
        # Get crew responses first (these can't be streamed)
        crew_responses = []
        if crew_to_consult:
            for member in crew_to_consult:
                cr = self._get_crew_response(member, message)
                crew_responses.append(cr)
                # Yield crew response marker
                yield f"[CREW:{member.marker}:{cr.content[:100]}...]"
        
        # Build messages for streaming
        messages = [
            {"role": "system", "content": self._build_nexus_system_prompt(task_type)},
        ]
        
        if crew_responses:
            crew_context = "CREW CONSULTATIONS:\n\n"
            for cr in crew_responses:
                crew_context += f"{cr.marker} {cr.name}: {cr.content[:200]}...\n\n"
            messages.append({
                "role": "system", 
                "content": crew_context + "\nConsider these crew perspectives."
            })
        
        messages.append({"role": "user", "content": message})
        
        request = APIRequest(
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=True,
            task_type=task_type,
        )
        
        try:
            yield from self._router.complete_stream(request)
            
            # Log action after streaming completes
            self.session.log_action(f"Streamed {task_type.value} response")
            
        except Exception as e:
            yield f"\n[ERROR] Error: {e}"
    
    def next_loop(self) -> None:
        """Advance to the next loop (session)."""
        self.session = self.session.next_loop()
    
    def get_status(self) -> dict:
        """Get current agent status."""
        # Get memory stats
        memory_info = self.memory_manager.get_session_info()
        
        return {
            "loop": self.session.loop_number,
            "status": self.session.status.value,
            "integrity": self.session.integrity.value,
            "budget": str(self.budget),
            "crew_count": len(self.crew),
            "precedents": len(self.precedent_log),
            "apis": self._router.is_configured() if self._router else {},
            "memory": memory_info,
        }
    
    def generate_session_summary(self) -> Optional[dict]:
        """
        Generate a summary of the current session and save it as a COMM.

        Uses the LLM to summarize recent conversation history.
        Returns the created communication details or None on failure.
        """
        if not self._router:
            return None

        # Get recent global history
        memory = self.memory_manager.get_memory()
        recent = memory.global_history[-20:]
        if not recent:
            return None

        history_text = "\n".join(
            f"{'Director' if m.role == 'director' else m.role.upper()}: {m.content[:200]}"
            for m in recent
        )

        messages = [
            {"role": "system", "content": (
                "You are NEXUS, the station AI. Summarize the following conversation "
                "into a concise session report (3-5 bullet points). Focus on decisions made, "
                "tasks discussed, and any actions taken. Be brief and factual."
            )},
            {"role": "user", "content": f"Summarize this session:\n\n{history_text}"},
        ]

        try:
            request = APIRequest(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                stream=False,
                task_type=TaskType.GENERAL,
            )
            response = self._router.complete(request)

            # Save as communication
            comm = self.memory_manager.create_communication(
                subject=f"Session Summary — Loop {self.session.loop_number}",
                content=response.content.strip(),
                from_member="NEXUS",
                comm_type="REPORT",
                priority="NORMAL",
            )

            return {
                "id": comm.id,
                "subject": comm.subject,
                "content": comm.content,
                "from_member": comm.from_member,
            }
        except Exception as e:
            print(f"[ERROR] Failed to generate session summary: {e}")
            return None

    # Task management methods (Jira-like)
    def create_task(self, title: str, description: str, assigned_to: str, priority: str = "MEDIUM") -> Task:
        """Create a new task assigned to a crew member."""
        return self.memory_manager.create_task(title, description, assigned_to, priority)
    
    def get_tasks(self, assigned_to: Optional[str] = None, status: Optional[str] = None) -> list[Task]:
        """Get tasks with optional filtering."""
        return self.memory_manager.get_tasks(assigned_to, status)
    
    def update_task_status(self, task_id: str, new_status: str) -> Optional[Task]:
        """Update task status."""
        return self.memory_manager.update_task_status(task_id, new_status)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        return self.memory_manager.delete_task(task_id)

    def delete_all_tasks(self) -> int:
        """Delete all tasks. Returns count deleted."""
        return self.memory_manager.delete_all_tasks()
    
    def get_character_memory(self, character: str) -> CharacterMemory:
        """Get memory for a specific character."""
        return self.memory_manager.get_character_memory(character)
    
    def get_character_history(self, character: str) -> list[Message]:
        """Get conversation history for a specific character."""
        return self.memory_manager.get_character_history(character)


def create_nexus_agent() -> NexusAgent:
    """
    Create and initialize a NEXUS agent with all systems.
    
    This automatically configures APIs from saved settings.
    """
    from .charter import create_standard_charter
    
    # Create charter
    charter = create_standard_charter(
        name="NEXUS STATION",
        institution_type="Deep Space Research Institute",
        aesthetic_era="1970s retrofuturism meets hard science fiction",
        core_tension=("DISCOVERY", "SAFETY"),
        description="A multinational research station orbiting at the L2 Lagrange point.",
    )
    charter.seal()
    
    # Create agent
    agent = NexusAgent(charter=charter)
    
    return agent
