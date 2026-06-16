"""
Visual Mind-Map Interface

Obsidian-style node-based visualization of the user's financial life.
Designed for full-screen mobile viewing so visual thinkers can literally
"see" their money flow, liabilities, and assets interconnected.

Implementation Strategy:
- Backend generates a graph data structure (nodes + edges)
- Frontend renders using D3.js force-directed graph or Cytoscape.js
- Each node is an account, bill, income source, or goal
- Edges represent money flow (income → account → bill/investment)
- Color coding by bucket type (Tax/Taxable/Free)
- Size of nodes proportional to dollar amounts
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class NodeType(Enum):
    INCOME = "income"
    ACCOUNT = "account"
    BILL = "bill"
    SUBSCRIPTION = "subscription"
    INVESTMENT = "investment"
    GOAL = "goal"
    HOUSEHOLD_MEMBER = "household_member"


class EdgeType(Enum):
    FLOWS_TO = "flows_to"          # Money moves from A to B
    PAYS_FOR = "pays_for"          # Account pays a bill
    CONTRIBUTES_TO = "contributes_to"  # Income contributes to account
    OWNED_BY = "owned_by"          # Account owned by household member


@dataclass
class MapNode:
    """A node in the financial mind map."""
    id: str
    label: str
    node_type: NodeType
    bucket_type: Optional[str] = None  # BUCKET_TAX, BUCKET_TAXABLE, BUCKET_FREE
    amount: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type.value,
            "bucket": self.bucket_type,
            "amount": self.amount,
            "size": self._calculate_size(),
            "color": self._get_color(),
            "metadata": self.metadata
        }

    def _calculate_size(self) -> int:
        """Node size proportional to dollar amount."""
        if self.amount <= 0:
            return 20
        elif self.amount < 100:
            return 25
        elif self.amount < 1000:
            return 35
        elif self.amount < 10000:
            return 50
        else:
            return 70

    def _get_color(self) -> str:
        """Color by bucket type."""
        colors = {
            "BUCKET_TAX": "#4A90D9",      # Blue — deferred
            "BUCKET_TAXABLE": "#E8A838",   # Gold — taxable
            "BUCKET_FREE": "#50C878",      # Green — exempt
        }
        type_colors = {
            NodeType.INCOME: "#7ED321",
            NodeType.BILL: "#D0021B",
            NodeType.SUBSCRIPTION: "#F5A623",
            NodeType.GOAL: "#9013FE",
            NodeType.HOUSEHOLD_MEMBER: "#4A4A4A",
        }
        if self.bucket_type:
            return colors.get(self.bucket_type, "#9B9B9B")
        return type_colors.get(self.node_type, "#9B9B9B")


@dataclass
class MapEdge:
    """An edge (connection) between two nodes."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    amount: float = 0.0
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type.value,
            "amount": self.amount,
            "label": self.label or self.edge_type.value.replace("_", " "),
            "width": self._calculate_width()
        }

    def _calculate_width(self) -> int:
        """Edge width proportional to flow amount."""
        if self.amount <= 0:
            return 1
        elif self.amount < 500:
            return 2
        elif self.amount < 2000:
            return 3
        else:
            return 5


@dataclass
class FinancialMindMap:
    """The complete financial mind map graph."""
    nodes: List[MapNode] = field(default_factory=list)
    edges: List[MapEdge] = field(default_factory=list)

    def add_node(self, node: MapNode):
        self.nodes.append(node)

    def add_edge(self, edge: MapEdge):
        self.edges.append(edge)

    def to_graph_data(self) -> dict:
        """Export as JSON-serializable graph data for the frontend."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "bucket_summary": self._bucket_summary()
            }
        }

    def _bucket_summary(self) -> dict:
        """Summarize totals by bucket type."""
        summary = {}
        for node in self.nodes:
            if node.bucket_type:
                if node.bucket_type not in summary:
                    summary[node.bucket_type] = 0.0
                summary[node.bucket_type] += node.amount
        return summary


def build_sample_map() -> FinancialMindMap:
    """Build a sample mind map for demonstration."""
    fmap = FinancialMindMap()

    # Income nodes
    fmap.add_node(MapNode("inc_salary", "Salary", NodeType.INCOME, amount=4500))

    # Account nodes
    fmap.add_node(MapNode("acc_checking", "Checking", NodeType.ACCOUNT, "BUCKET_TAXABLE", 2300))
    fmap.add_node(MapNode("acc_savings", "Savings", NodeType.ACCOUNT, "BUCKET_TAXABLE", 8500))
    fmap.add_node(MapNode("acc_401k", "401(k)", NodeType.ACCOUNT, "BUCKET_TAX", 45000))
    fmap.add_node(MapNode("acc_roth", "Roth IRA", NodeType.ACCOUNT, "BUCKET_FREE", 12000))

    # Bill nodes
    fmap.add_node(MapNode("bill_rent", "Rent", NodeType.BILL, amount=1400))
    fmap.add_node(MapNode("bill_car", "Car Payment", NodeType.BILL, amount=350))
    fmap.add_node(MapNode("sub_netflix", "Netflix", NodeType.SUBSCRIPTION, amount=15.99))
    fmap.add_node(MapNode("sub_gym", "Gym", NodeType.SUBSCRIPTION, amount=49.99))

    # Edges (money flow)
    fmap.add_edge(MapEdge("inc_salary", "acc_checking", EdgeType.CONTRIBUTES_TO, 4500))
    fmap.add_edge(MapEdge("acc_checking", "bill_rent", EdgeType.PAYS_FOR, 1400))
    fmap.add_edge(MapEdge("acc_checking", "bill_car", EdgeType.PAYS_FOR, 350))
    fmap.add_edge(MapEdge("acc_checking", "sub_netflix", EdgeType.PAYS_FOR, 15.99))
    fmap.add_edge(MapEdge("acc_checking", "sub_gym", EdgeType.PAYS_FOR, 49.99))
    fmap.add_edge(MapEdge("acc_checking", "acc_savings", EdgeType.FLOWS_TO, 500))
    fmap.add_edge(MapEdge("inc_salary", "acc_401k", EdgeType.CONTRIBUTES_TO, 675))

    return fmap
