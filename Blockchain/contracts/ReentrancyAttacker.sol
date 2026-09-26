// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IEscrow {

    function createEscrow(
        string memory agentId,
        address provider,
        bytes32 serviceHash,
        uint256 deadline
    )
        external
        payable
        returns (uint256);

    function releaseEscrow(
        uint256 escrowId
    )
        external;
}

interface IAgentRegistry {

    function registerAgent(
        string memory agentId,
        string memory serviceType
    )
        external;
}

contract ReentrancyAttacker {

    IEscrow public escrow;

    IAgentRegistry public registry;

    address public provider;

    uint256 public targetEscrowId;

    bool public attackStarted;


    constructor(
        address _escrow,
        address _registry
    ) {
        escrow = IEscrow(_escrow);

        registry = IAgentRegistry(_registry);
    }


    // --------------------------------------------------
    // Register this contract as the BUYER agent
    // --------------------------------------------------

    function registerBuyerAgent(
        string memory agentId
    )
        external
    {
        registry.registerAgent(
            agentId,
            "Buyer Agent"
        );
    }


    // --------------------------------------------------
    // Set malicious provider
    // --------------------------------------------------

    function setProvider(
        address _provider
    )
        external
    {
        provider = _provider;
    }


    // --------------------------------------------------
    // Create escrow
    // --------------------------------------------------

    function createEscrow(
        string memory agentId,
        bytes32 serviceHash,
        uint256 deadline
    )
        external
        payable
        returns (uint256)
    {
        return escrow.createEscrow{
            value: msg.value
        }(
            agentId,
            provider,
            serviceHash,
            deadline
        );
    }


    // --------------------------------------------------
    // Start the attack
    //
    // IMPORTANT:
    // This function is called by the test account.
    //
    // But the actual Escrow call is made by THIS
    // contract, so Escrow sees this contract as buyer.
    // --------------------------------------------------

    function startAttack(
        uint256 escrowId
    )
        external
    {
        targetEscrowId = escrowId;

        attackStarted = true;

        escrow.releaseEscrow(
            escrowId
        );
    }


    // --------------------------------------------------
    // Re-enter Escrow
    //
    // MaliciousProvider calls this function when it
    // receives ETH.
    //
    // Escrow sees THIS contract as msg.sender.
    // Therefore onlyBuyer passes.
    //
    // Then nonReentrant blocks the second call.
    // --------------------------------------------------

    function reenterEscrow()
        external
    {
        require(
            msg.sender == provider,
            "Only provider"
        );

        escrow.releaseEscrow(
            targetEscrowId
        );
    }
}