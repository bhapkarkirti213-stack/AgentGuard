// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Reputation {

    address public owner;

    mapping(address => bool) public authorizedUpdaters;

    struct ReputationData {
        uint256 successfulTransactions;
        uint256 failedTransactions;
        uint256 refundedTransactions;
        uint256 disputes;

        uint256 totalTransactionValue;
        uint256 successfulTransactionValue;

        uint256 lastUpdated;
    }

    mapping(address => ReputationData) private reputations;

    event UpdaterAuthorizationChanged(
        address indexed updater,
        bool authorized
    );

    event ReputationUpdated(
        address indexed agent,
        uint256 reputationScore
    );

    modifier onlyOwner() {
        require(
            msg.sender == owner,
            "Only owner"
        );
        _;
    }

    modifier onlyAuthorizedUpdater() {
        require(
            authorizedUpdaters[msg.sender],
            "Not authorized updater"
        );
        _;
    }

    constructor() {
        owner = msg.sender;

        authorizedUpdaters[msg.sender] = true;

        emit UpdaterAuthorizationChanged(
            msg.sender,
            true
        );
    }

    // ---------------------------------------------------------
    // AUTHORIZATION
    // ---------------------------------------------------------

    function setAuthorizedUpdater(
        address updater,
        bool authorized
    )
        external
        onlyOwner
    {
        require(
            updater != address(0),
            "Invalid updater"
        );

        authorizedUpdaters[updater] = authorized;

        emit UpdaterAuthorizationChanged(
            updater,
            authorized
        );
    }

    // ---------------------------------------------------------
    // SUCCESS
    // ---------------------------------------------------------

    function recordSuccess(
        address agent,
        uint256 value
    )
        external
        onlyAuthorizedUpdater
    {
        require(
            agent != address(0),
            "Invalid agent"
        );

        ReputationData storage data =
            reputations[agent];

        data.successfulTransactions += 1;

        data.totalTransactionValue += value;

        data.successfulTransactionValue += value;

        data.lastUpdated = block.timestamp;

        emit ReputationUpdated(
            agent,
            calculateScore(agent)
        );
    }

    // ---------------------------------------------------------
    // FAILURE
    // ---------------------------------------------------------

    function recordFailure(
        address agent,
        uint256 value
    )
        external
        onlyAuthorizedUpdater
    {
        require(
            agent != address(0),
            "Invalid agent"
        );

        ReputationData storage data =
            reputations[agent];

        data.failedTransactions += 1;

        data.totalTransactionValue += value;

        data.lastUpdated = block.timestamp;

        emit ReputationUpdated(
            agent,
            calculateScore(agent)
        );
    }

    // ---------------------------------------------------------
    // REFUND
    // ---------------------------------------------------------

    function recordRefund(
        address agent
    )
        external
        onlyAuthorizedUpdater
    {
        require(
            agent != address(0),
            "Invalid agent"
        );

        ReputationData storage data =
            reputations[agent];

        uint256 completedTransactions =
            data.successfulTransactions +
            data.failedTransactions;

        require(
            data.refundedTransactions <
            completedTransactions,
            "Invalid refund count"
        );

        data.refundedTransactions += 1;

        data.lastUpdated = block.timestamp;

        emit ReputationUpdated(
            agent,
            calculateScore(agent)
        );
    }

    // ---------------------------------------------------------
    // DISPUTE
    // ---------------------------------------------------------

    function recordDispute(
        address agent
    )
        external
        onlyAuthorizedUpdater
    {
        require(
            agent != address(0),
            "Invalid agent"
        );

        ReputationData storage data =
            reputations[agent];

        uint256 completedTransactions =
            data.successfulTransactions +
            data.failedTransactions;

        require(
            data.disputes <
            completedTransactions,
            "Invalid dispute count"
        );

        data.disputes += 1;

        data.lastUpdated = block.timestamp;

        emit ReputationUpdated(
            agent,
            calculateScore(agent)
        );
    }

    // ---------------------------------------------------------
    // CALCULATE SCORE
    // ---------------------------------------------------------

    function calculateScore(
        address agent
    )
        public
        view
        returns (uint256)
    {
        ReputationData memory data =
            reputations[agent];

        uint256 completedTransactions =
            data.successfulTransactions +
            data.failedTransactions;

        if (completedTransactions == 0) {
            return 0;
        }

        uint256 successRate =
            (data.successfulTransactions * 100) /
            completedTransactions;

        uint256 refundRate =
            (data.refundedTransactions * 100) /
            completedTransactions;

        uint256 disputeRate =
            (data.disputes * 100) /
            completedTransactions;

        return (
            60 * successRate +
            25 * (100 - refundRate) +
            15 * (100 - disputeRate)
        ) / 100;
    }

    // ---------------------------------------------------------
    // GET REPUTATION DATA
    // ---------------------------------------------------------

    function getReputation(
        address agent
    )
        external
        view
        returns (ReputationData memory data)
    {
        data = reputations[agent];
    }

    // ---------------------------------------------------------
    // GET SCORE
    // ---------------------------------------------------------

    function getReputationScore(
        address agent
    )
        external
        view
        returns (uint256)
    {
        return calculateScore(agent);
    }
}