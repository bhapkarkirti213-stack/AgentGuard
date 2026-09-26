// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentRegistry {

    function registerAgent(
        string memory agentId,
        string memory serviceType
    )
        external;
}

interface IReentrancyAttacker {

    function reenterEscrow()
        external;
}

contract MaliciousProvider {

    IAgentRegistry public registry;

    address public attacker;

    uint256 public targetEscrowId;

    bool public attackStarted;

    bool public reentrancyBlocked;


    constructor(
        address _escrow,
        address _registry
    ) {
        registry = IAgentRegistry(_registry);
    }


    // --------------------------------------------------
    // Register provider
    // --------------------------------------------------

    function registerProviderAgent(
        string memory agentId
    )
        external
    {
        registry.registerAgent(
            agentId,
            "Malicious Provider"
        );
    }


    // --------------------------------------------------
    // Set buyer/attacker contract
    // --------------------------------------------------

    function setAttacker(
        address _attacker
    )
        external
    {
        attacker = _attacker;
    }


    // --------------------------------------------------
    // Set target escrow
    // --------------------------------------------------

    function setTargetEscrow(
        uint256 escrowId
    )
        external
    {
        targetEscrowId = escrowId;
    }


    // --------------------------------------------------
    // Enable attack
    // --------------------------------------------------

    function enableAttack()
        external
    {
        attackStarted = true;

        reentrancyBlocked = false;
    }


    // --------------------------------------------------
    // Receive ETH
    //
    // Escrow sends payment here.
    //
    // We attempt to re-enter the Escrow through the
    // buyer contract.
    //
    // The reentrancy guard should reject that call.
    // We catch the failure so the original payment
    // can continue successfully.
    // --------------------------------------------------

    receive()
        external
        payable
    {
        if (attackStarted) {

            attackStarted = false;

            try IReentrancyAttacker(
                attacker
            ).reenterEscrow()
            {
                // If this succeeds, the reentrancy
                // protection failed.
                reentrancyBlocked = false;
            }
            catch {

                // The reentrant call was rejected.
                reentrancyBlocked = true;
            }
        }
    }
}