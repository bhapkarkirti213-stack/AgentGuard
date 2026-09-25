// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;

contract AgentRegistry {

    struct Agent {
        string agentId;
        address wallet;
        string serviceType;
        bool active;
        uint256 registeredAt;
    }

    mapping(string => Agent) private agents;

    event AgentRegistered(
        string agentId,
        address wallet,
        string serviceType,
        uint256 registeredAt
    );

    function registerAgent(
        string memory _agentId,
        string memory _serviceType
    ) public {

        require(
            agents[_agentId].wallet == address(0),
            "Agent already registered"
        );

        agents[_agentId] = Agent(
            _agentId,
            msg.sender,
            _serviceType,
            true,
            block.timestamp
        );

        emit AgentRegistered(
            _agentId,
            msg.sender,
            _serviceType,
            block.timestamp
        );
    }

    function getAgent(
        string memory _agentId
    )
        public
        view
        returns (
            string memory agentId,
            address wallet,
            string memory serviceType,
            bool active,
            uint256 registeredAt
        )
    {
        Agent memory agent = agents[_agentId];

        return (
            agent.agentId,
            agent.wallet,
            agent.serviceType,
            agent.active,
            agent.registeredAt
        );
    }
}