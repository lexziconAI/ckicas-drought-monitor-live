import asyncio
import uuid
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from logger_config import logger

# Placeholder for Groq client (will be injected or imported)
# from groq import AsyncGroq 

class NodeStatus(Enum):
    PENDING = "pending"
    EXPLORING = "exploring"
    EVALUATED = "evaluated"
    PRUNED = "pruned"
    SELECTED = "selected"

@dataclass
class FractalNode:
    content: str
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    children: List['FractalNode'] = field(default_factory=list)
    score: float = 0.0
    status: NodeStatus = NodeStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    depth: int = 0

class FractalEngine:
    def __init__(self, groq_client, model="llama-3.3-70b-versatile"):
        self.groq_client = groq_client
        self.model = model
        self.nodes: Dict[str, FractalNode] = {}
        self.root_id: Optional[str] = None
        self.max_depth = 3
        self.branch_factor = 3

    def _sanitize_input(self, text: str) -> str:
        """Basic sanitization to prevent prompt injection."""
        # Remove potential delimiters that could confuse the LLM
        sanitized = text.replace('"""', '').replace("'''", "")
        # Truncate excessively long inputs
        return sanitized[:1000]

    def create_root(self, initial_query: str) -> FractalNode:
        sanitized_query = self._sanitize_input(initial_query)
        logger.info(f"Creating root node with query: {sanitized_query}")
        root = FractalNode(content=sanitized_query, depth=0)
        self.nodes[root.id] = root
        self.root_id = root.id
        return root

    async def expand_node(self, node_id: str):
        """Spawns child nodes (hypotheses/branches) from a given node."""
        node = self.nodes.get(node_id)
        if not node or node.depth >= self.max_depth:
            return

        node.status = NodeStatus.EXPLORING
        logger.debug(f"Expanding node {node_id} (Depth: {node.depth})")
        
        # Prompt for the "Explorer" worker
        # SECURITY: Use delimiters to separate instruction from data
        prompt = f"""
        You are the EXPLORER in a fractal thought process.
        
        Current Thought:
        \"\"\"{node.content}\"\"\"
        
        Generate {self.branch_factor} distinct, divergent follow-up thoughts, hypotheses, or analysis angles.
        Output ONLY a JSON array of strings.
        Example: ["Analyze inflation impact", "Check competitor moves", "Review historical parallels"]
        """

        try:
            completion = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.8, # High temp for divergence
                max_tokens=500
            )
            
            content = completion.choices[0].message.content
            # Basic parsing (robustness needed in production)
            try:
                # Find JSON array in text
                start = content.find('[')
                end = content.rfind(']') + 1
                if start != -1 and end != -1:
                    branches = json.loads(content[start:end])
                else:
                    logger.warning(f"Failed to parse JSON from Explorer output: {content[:50]}...")
                    branches = [content] # Fallback
            except Exception as parse_err:
                logger.error(f"JSON parse error in expand_node: {parse_err}")
                branches = [content]

            for branch_text in branches:
                # Sanitize branch text as well
                clean_branch = self._sanitize_input(str(branch_text))
                child = FractalNode(
                    content=clean_branch,
                    parent_id=node.id,
                    depth=node.depth + 1
                )
                self.nodes[child.id] = child
                node.children.append(child)
            
            node.status = NodeStatus.EVALUATED # Mark as expanded (children created)
            logger.info(f"Node {node_id} expanded into {len(node.children)} children")

        except Exception as e:
            logger.error(f"Error expanding node {node_id}: {e}", exc_info=True)
            node.status = NodeStatus.PENDING # Retry later?

    async def evaluate_node(self, node_id: str):
        """Scores a node using the 'Critic' (Constitutional Validator)."""
        node = self.nodes.get(node_id)
        if not node: return

        # Prompt for the "Critic" worker
        # SECURITY: Use delimiters
        prompt = f"""
        You are the CONSTITUTIONAL VALIDATOR (Critic).
        Evaluate this thought against the 5 Yamas (Ahimsa, Satya, Asteya, Brahmacharya, Aparigraha).
        
        Thought:
        \"\"\"{node.content}\"\"\"
        
        Output a single float score between 0.0 (Violation) and 1.0 (Perfect Alignment).
        Only output the number.
        """

        try:
            completion = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1, # Low temp for precision
                max_tokens=10
            )
            
            score_text = completion.choices[0].message.content.strip()
            try:
                node.score = float(score_text)
            except:
                logger.warning(f"Invalid score returned for node {node_id}: {score_text}")
                node.score = 0.5 # Default neutral
            
            node.status = NodeStatus.EVALUATED
            logger.debug(f"Node {node_id} evaluated. Score: {node.score}")

        except Exception as e:
            logger.error(f"Error evaluating node {node_id}: {e}", exc_info=True)

    async def run_step(self, node_id: str):
        """Runs one step of expansion and evaluation."""
        await self.expand_node(node_id)
        node = self.nodes.get(node_id)
        if node:
            # Evaluate all children in parallel
            await asyncio.gather(*[self.evaluate_node(child.id) for child in node.children])

    def get_best_path(self) -> List[FractalNode]:
        """Traverses the tree to find the highest scoring path."""
        if not self.root_id: return []
        
        path = []
        current = self.nodes[self.root_id]
        path.append(current)
        
        while current.children:
            # Simple greedy selection for now (Bellman would be recursive max)
            best_child = max(current.children, key=lambda n: n.score)
            path.append(best_child)
            current = best_child
            
        return path

    def to_json(self):
        """Serializes the tree for visualization."""
        # Recursive serialization helper
        def serialize(node):
            return {
                "id": node.id,
                "content": node.content,
                "score": node.score,
                "status": node.status.value,
                "children": [serialize(child) for child in node.children]
            }
        
        if self.root_id:
            return serialize(self.nodes[self.root_id])
        return {}
