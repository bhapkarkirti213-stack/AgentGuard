// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentRegistry {

    function getAgent(
        string memory agentId
    )
        external
        view
        returns (
            string memory,
            address,
            string memory,
            bool,
            uint256
        );
}

interface IReputation {

    function recordSuccess(
        address agent,
        uint256 value
    )
        external;

    function recordFailure(
        address agent,
        uint256 value
    )
        external;

    function recordRefund(
        address agent
    )
        external;

    function recordDispute(
        address agent
    )
        external;
}

contract Escrow {

    enum Status {
        Created,
        Funded,
        Released,
        Refunded
    }

    struct EscrowData {

        address buyer;

        address provider;

        string agentId;

        uint256 amount;

        bytes32 serviceHash;

        uint256 createdAt;

        uint256 deadline;

        Status status;
    }

    address public owner;

    IAgentRegistry public agentRegistry;

    IReputation public reputation;

    uint256 private nextEscrowId = 1;

    uint256 private locked = 1;

    mapping(
        uint256 => EscrowData
    ) private escrows;


    // --------------------------------------------------
    // EVENTS
    // --------------------------------------------------

    event AgentRegistryUpdated(
        address indexed registry
    );

    event ReputationContractUpdated(
        address indexed reputation
    );

    event EscrowCreated(
        uint256 indexed escrowId,
        address indexed buyer,
        address indexed provider,
        string agentId,
        uint256 amount,
        bytes32 serviceHash,
        uint256 deadline
    );

    event EscrowReleased(
        uint256 indexed escrowId,
        address indexed provider,
        uint256 amount
    );

    event EscrowRefunded(
        uint256 indexed escrowId,
        address indexed buyer,
        uint256 amount
    );


    // --------------------------------------------------
    // MODIFIERS
    // --------------------------------------------------

    modifier onlyOwner() {

        require(
            msg.sender == owner,
            "Only owner"
        );

        _;
    }


    modifier onlyBuyer(
        uint256 escrowId
    ) {

        require(
            msg.sender ==
            escrows[escrowId].buyer,
            "Only buyer"
        );

        _;
    }


    modifier nonReentrant() {

        require(
            locked == 1,
            "ReentrancyGuard: reentrant call"
        );

        locked = 2;

        _;

        locked = 1;
    }


    // --------------------------------------------------
    // CONSTRUCTOR
    // --------------------------------------------------

    constructor() {

        owner = msg.sender;
    }


    // --------------------------------------------------
    // SET AGENT REGISTRY
    // --------------------------------------------------

    function setAgentRegistry(
        address registryAddress
    )
        external
        onlyOwner
    {

        require(
            registryAddress != address(0),
            "Invalid registry"
        );

        agentRegistry =
            IAgentRegistry(
                registryAddress
            );

        emit AgentRegistryUpdated(
            registryAddress
        );
    }


    // --------------------------------------------------
    // SET REPUTATION CONTRACT
    // --------------------------------------------------

    function setReputationContract(
        address reputationAddress
    )
        external
        onlyOwner
    {

        require(
            reputationAddress != address(0),
            "Invalid reputation"
        );

        reputation =
            IReputation(
                reputationAddress
            );

        emit ReputationContractUpdated(
            reputationAddress
        );
    }


    // --------------------------------------------------
    // CREATE ESCROW
    // --------------------------------------------------

    function createEscrow(
        string memory agentId,
        address provider,
        bytes32 serviceHash,
        uint256 deadline
    )
        external
        payable
        returns (
            uint256 escrowId
        )
    {

        require(
            address(agentRegistry) !=
            address(0),
            "Registry not configured"
        );


        require(
            provider != address(0),
            "Invalid provider"
        );


        require(
            provider != msg.sender,
            "Buyer cannot be provider"
        );


        require(
            msg.value > 0,
            "Amount must be greater than zero"
        );


        require(
            deadline > block.timestamp,
            "Invalid deadline"
        );


        (
            ,
            address registeredWallet,
            ,
            bool active,
            
        ) =
            agentRegistry.getAgent(
                agentId
            );


        require(
            registeredWallet != address(0),
            "Agent not registered"
        );


        require(
            registeredWallet == provider,
            "Provider mismatch"
        );


        require(
            active,
            "Agent inactive"
        );


        escrowId = nextEscrowId++;


        escrows[escrowId] =
            EscrowData({

                buyer: msg.sender,

                provider: provider,

                agentId: agentId,

                amount: msg.value,

                serviceHash: serviceHash,

                createdAt: block.timestamp,

                deadline: deadline,

                status: Status.Funded
            });


        emit EscrowCreated(

            escrowId,

            msg.sender,

            provider,

            agentId,

            msg.value,

            serviceHash,

            deadline
        );
    }


    // --------------------------------------------------
    // RELEASE ESCROW
    // --------------------------------------------------
    //
    // IMPORTANT:
    // nonReentrant is intentionally BEFORE onlyBuyer.
    //
    // This means a callback/reentrant call is stopped
    // immediately by the reentrancy guard.
    // --------------------------------------------------

    function releaseEscrow(
        uint256 escrowId
    )
        external
        nonReentrant
        onlyBuyer(escrowId)
    {

        EscrowData storage escrow =
            escrows[escrowId];


        require(
            escrow.status ==
            Status.Funded,
            "Escrow not funded"
        );


        escrow.status =
            Status.Released;


        uint256 amount =
            escrow.amount;


        address provider =
            escrow.provider;


        (bool success, ) =
            payable(provider).call{
                value: amount
            }("");


        require(
            success,
            "Payment failed"
        );


        // Update reputation after successful payment
        if (
            address(reputation) !=
            address(0)
        ) {

            reputation.recordSuccess(
                provider,
                amount
            );
        }


        emit EscrowReleased(

            escrowId,

            provider,

            amount
        );
    }


    // --------------------------------------------------
    // REFUND ESCROW
    // --------------------------------------------------
    //
    // nonReentrant is also placed before onlyBuyer.
    // --------------------------------------------------

    function refundEscrow(
        uint256 escrowId
    )
        external
        nonReentrant
        onlyBuyer(escrowId)
    {

        EscrowData storage escrow =
            escrows[escrowId];


        require(
            escrow.status ==
            Status.Funded,
            "Escrow not funded"
        );


        require(
            block.timestamp >=
            escrow.deadline,
            "Deadline not reached"
        );


        escrow.status =
            Status.Refunded;


        uint256 amount =
            escrow.amount;


        address buyer =
            escrow.buyer;


        (bool success, ) =
            payable(buyer).call{
                value: amount
            }("");


        require(
            success,
            "Refund failed"
        );


        // Update reputation after refund
        if (
            address(reputation) !=
            address(0)
        ) {

            reputation.recordFailure(
                escrow.provider,
                amount
            );


            reputation.recordRefund(
                escrow.provider
            );
        }


        emit EscrowRefunded(

            escrowId,

            buyer,

            amount
        );
    }


    // --------------------------------------------------
    // GET ESCROW
    // --------------------------------------------------

    function getEscrow(
        uint256 escrowId
    )
        external
        view
        returns (
            EscrowData memory
        )
    {

        require(
            escrowId > 0 &&
            escrowId < nextEscrowId,
            "Escrow does not exist"
        );


        return escrows[escrowId];
    }


    // --------------------------------------------------
    // GET ESCROW COUNT
    // --------------------------------------------------

    function getEscrowCount()
        external
        view
        returns (
            uint256
        )
    {

        return nextEscrowId - 1;
    }
}