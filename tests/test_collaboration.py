"""
Unit tests for core.collaboration.protocol module
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

import pytest

from core.collaboration.protocol import (AgentIdentity, CollaborationMessage,
                                         CollaborationProtocol, Consensus,
                                         ConsensusStrategy, DelegationStrategy,
                                         MessageType, TaskProposal, Vote,
                                         VoteValue)


@pytest.fixture
def protocol():
    """Create a CollaborationProtocol instance"""
    return CollaborationProtocol("test_agent")


@pytest.fixture
def agent_identities():
    """Create test agent identities"""
    return [
        AgentIdentity(
            agent_id=f"agent_{i}",
            capabilities={"reasoning", "analysis"},
            reputation=0.8 + i * 0.05
        )
        for i in range(5)
    ]


class TestCollaborationMessage:
    """Test CollaborationMessage class"""

    def test_create_message(self):
        """Test creating a collaboration message"""

        msg = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender="agent_1",
            receiver="agent_2",
            content={"task": "test"},
            priority=1
        )

        assert msg.message_type == MessageType.REQUEST
        assert msg.sender == "agent_1"
        assert msg.receiver == "agent_2"
        assert msg.content["task"] == "test"
        assert msg.priority == 1

    def test_message_to_dict(self):
        """Test converting message to dictionary"""

        msg = CollaborationMessage(
            message_type=MessageType.PROPOSAL,
            sender="agent_1",
            receiver="agent_2",
            content={"proposal": "data"}
        )

        msg_dict = msg.to_dict()

        assert msg_dict["message_type"] == "PROPOSAL"
        assert msg_dict["sender"] == "agent_1"
        assert msg_dict["receiver"] == "agent_2"
        assert "timestamp" in msg_dict


class TestTaskProposal:
    """Test TaskProposal class"""

    def test_create_proposal(self):
        """Test creating a task proposal"""

        proposal = TaskProposal(
            task_id="task_1",
            description="Test task",
            proposer="agent_1",
            required_capabilities={"reasoning"},
            estimated_effort=5.0
        )

        assert proposal.task_id == "task_1"
        assert proposal.proposer == "agent_1"
        assert "reasoning" in proposal.required_capabilities
        assert proposal.estimated_effort == 5.0

    def test_proposal_to_dict(self):
        """Test converting proposal to dictionary"""

        proposal = TaskProposal(
            task_id="task_1",
            description="Test",
            proposer="agent_1"
        )

        proposal_dict = proposal.to_dict()

        assert proposal_dict["task_id"] == "task_1"
        assert proposal_dict["proposer"] == "agent_1"
        assert "timestamp" in proposal_dict


class TestVote:
    """Test Vote class"""

    def test_create_vote(self):
        """Test creating a vote"""

        vote = Vote(
            voter="agent_1",
            value=VoteValue.APPROVE,
            weight=1.0,
            reasoning="Looks good"
        )

        assert vote.voter == "agent_1"
        assert vote.value == VoteValue.APPROVE
        assert vote.weight == 1.0
        assert vote.reasoning == "Looks good"

    def test_vote_values(self):
        """Test vote value options"""

        assert VoteValue.APPROVE.value == 1
        assert VoteValue.REJECT.value == 0
        assert VoteValue.ABSTAIN.value == -1


class TestAgentIdentity:
    """Test AgentIdentity class"""

    def test_create_identity(self):
        """Test creating agent identity"""

        identity = AgentIdentity(
            agent_id="agent_1",
            capabilities={"reasoning", "analysis"},
            reputation=0.85
        )

        assert identity.agent_id == "agent_1"
        assert len(identity.capabilities) == 2
        assert identity.reputation == 0.85

    def test_identity_with_metadata(self):
        """Test identity with metadata"""

        identity = AgentIdentity(
            agent_id="agent_1",
            capabilities={"reasoning"},
            reputation=0.8,
            metadata={"specialization": "logic"}
        )

        assert identity.metadata["specialization"] == "logic"


class TestCollaborationProtocol:
    """Test CollaborationProtocol class"""

    def test_register_agent(self, protocol, agent_identities):
        """Test registering agents"""

        for identity in agent_identities:
            protocol.register_agent(identity)

        assert len(protocol.agents) == 5
        assert "agent_0" in protocol.agents

    def test_get_agent(self, protocol, agent_identities):
        """Test retrieving agent by ID"""

        protocol.register_agent(agent_identities[0])

        agent = protocol.get_agent("agent_0")
        assert agent is not None
        assert agent.agent_id == "agent_0"

    @pytest.mark.asyncio
    async def test_send_message(self, protocol, agent_identities):
        """Test sending a message"""

        protocol.register_agent(agent_identities[0])
        protocol.register_agent(agent_identities[1])

        msg = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender="agent_0",
            receiver="agent_1",
            content={"data": "test"}
        )

        await protocol.send_message(msg)

        # Check message queue
        assert len(protocol.message_queue) == 1
        assert protocol.message_queue[0].sender == "agent_0"

    @pytest.mark.asyncio
    async def test_broadcast_message(self, protocol, agent_identities):
        """Test broadcasting message to all agents"""

        for identity in agent_identities:
            protocol.register_agent(identity)

        msg = CollaborationMessage(
            message_type=MessageType.BROADCAST,
            sender="agent_0",
            receiver="*",
            content={"announcement": "test"}
        )

        await protocol.broadcast_message(msg)

        # Should have messages for all other agents (4 total)
        assert len(protocol.message_queue) >= 4

    @pytest.mark.asyncio
    async def test_get_messages(self, protocol):
        """Test retrieving messages for an agent"""

        msg1 = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender="agent_0",
            receiver="agent_1",
            content={}
        )

        msg2 = CollaborationMessage(
            message_type=MessageType.RESPONSE,
            sender="agent_2",
            receiver="agent_1",
            content={}
        )

        await protocol.send_message(msg1)
        await protocol.send_message(msg2)

        messages = await protocol.get_messages("agent_1")

        assert len(messages) == 2


class TestTaskDelegation:
    """Test task delegation strategies"""

    @pytest.mark.asyncio
    async def test_delegate_capability_match(self, protocol, agent_identities):
        """Test capability-based delegation"""

        for identity in agent_identities:
            protocol.register_agent(identity)

        proposal = TaskProposal(
            task_id="task_1",
            description="Test task",
            proposer="agent_0",
            required_capabilities={"reasoning"}
        )

        selected = await protocol.delegate_task(
            proposal,
            strategy=DelegationStrategy.CAPABILITY_MATCH
        )

        assert selected is not None
        assert "reasoning" in selected.capabilities

    @pytest.mark.asyncio
    async def test_delegate_load_balance(self, protocol, agent_identities):
        """Test load-balanced delegation"""

        for identity in agent_identities:
            protocol.register_agent(identity)

        proposal = TaskProposal(
            task_id="task_1",
            description="Test",
            proposer="agent_0"
        )

        selected = await protocol.delegate_task(
            proposal,
            strategy=DelegationStrategy.LOAD_BALANCE
        )

        assert selected is not None
        assert protocol.task_loads[selected.agent_id] == 1

    @pytest.mark.asyncio
    async def test_delegate_priority_based(self, protocol, agent_identities):
        """Test priority-based delegation"""

        for identity in agent_identities:
            protocol.register_agent(identity)

        proposal = TaskProposal(
            task_id="task_1",
            description="High priority task",
            proposer="agent_0",
            priority=10
        )

        selected = await protocol.delegate_task(
            proposal,
            strategy=DelegationStrategy.PRIORITY_BASED
        )

        assert selected is not None
        # Should select agent with highest reputation
        assert selected.reputation >= 0.8


class TestConsensusBuilding:
    """Test consensus building strategies"""

    @pytest.mark.asyncio
    async def test_consensus_unanimous(self, protocol):
        """Test unanimous consensus"""

        votes = [
            Vote(voter=f"agent_{i}", value=VoteValue.APPROVE, weight=1.0)
            for i in range(5)
        ]

        consensus = await protocol.build_consensus(
            votes,
            strategy=ConsensusStrategy.UNANIMOUS
        )

        assert consensus.reached == True
        assert consensus.approval_ratio == 1.0

    @pytest.mark.asyncio
    async def test_consensus_majority(self, protocol):
        """Test majority consensus"""

        votes = [
            Vote(voter="agent_0", value=VoteValue.APPROVE, weight=1.0),
            Vote(voter="agent_1", value=VoteValue.APPROVE, weight=1.0),
            Vote(voter="agent_2", value=VoteValue.APPROVE, weight=1.0),
            Vote(voter="agent_3", value=VoteValue.REJECT, weight=1.0),
            Vote(voter="agent_4", value=VoteValue.REJECT, weight=1.0),
        ]

        consensus = await protocol.build_consensus(
            votes,
            strategy=ConsensusStrategy.MAJORITY
        )

        assert consensus.reached == True
        assert consensus.approval_ratio == 0.6

    @pytest.mark.asyncio
    async def test_consensus_weighted(self, protocol):
        """Test weighted consensus"""

        votes = [
            Vote(voter="agent_0", value=VoteValue.APPROVE, weight=2.0),
            Vote(voter="agent_1", value=VoteValue.APPROVE, weight=1.0),
            Vote(voter="agent_2", value=VoteValue.REJECT, weight=1.0),
        ]

        consensus = await protocol.build_consensus(
            votes,
            strategy=ConsensusStrategy.WEIGHTED
        )

        assert consensus.reached == True
        # Weighted: (2.0 + 1.0) / (2.0 + 1.0 + 1.0) = 0.75
        assert consensus.approval_ratio == 0.75

    @pytest.mark.asyncio
    async def test_consensus_not_reached(self, protocol):
        """Test consensus not reached"""

        votes = [
            Vote(voter="agent_0", value=VoteValue.REJECT, weight=1.0),
            Vote(voter="agent_1", value=VoteValue.REJECT, weight=1.0),
            Vote(voter="agent_2", value=VoteValue.REJECT, weight=1.0),
        ]

        consensus = await protocol.build_consensus(
            votes,
            strategy=ConsensusStrategy.UNANIMOUS
        )

        assert consensus.reached == False


class TestIntegration:
    """Integration tests for collaboration protocol"""

    @pytest.mark.asyncio
    async def test_full_collaboration_workflow(self, protocol, agent_identities):
        """Test complete collaboration workflow"""

        # 1. Register agents
        for identity in agent_identities:
            protocol.register_agent(identity)

        # 2. Create proposal
        proposal = TaskProposal(
            task_id="integration_test",
            description="Integration test task",
            proposer="agent_0",
            required_capabilities={"reasoning"}
        )

        # 3. Delegate task
        selected_agent = await protocol.delegate_task(
            proposal,
            strategy=DelegationStrategy.CAPABILITY_MATCH
        )

        assert selected_agent is not None

        # 4. Broadcast proposal
        msg = CollaborationMessage(
            message_type=MessageType.PROPOSAL,
            sender="agent_0",
            receiver="*",
            content=proposal.to_dict()
        )

        await protocol.broadcast_message(msg)

        # 5. Collect votes
        votes = [
            Vote(
                voter=agent.agent_id,
                value=VoteValue.APPROVE,
                weight=agent.reputation
            )
            for agent in agent_identities
        ]

        # 6. Build consensus
        consensus = await protocol.build_consensus(
            votes,
            strategy=ConsensusStrategy.WEIGHTED
        )

        assert consensus.reached == True

        # 7. Update reputation
        protocol.update_reputation("agent_0", 0.1)
        updated_agent = protocol.get_agent("agent_0")
        assert updated_agent.reputation > agent_identities[0].reputation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
