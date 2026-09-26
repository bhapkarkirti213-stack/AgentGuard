// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ServiceVerifier {

    address public owner;

    enum VerificationStatus {
        Pending,
        Valid,
        Invalid
    }

    struct Verification {
        uint256 escrowId;
        address provider;
        bytes32 requestHash;
        bytes32 resultHash;
        VerificationStatus status;
        uint256 verifiedAt;
    }

    mapping(uint256 => Verification) private verifications;

    event ServiceVerificationCreated(
        uint256 indexed escrowId,
        address indexed provider,
        bytes32 requestHash
    );

    event ServiceVerified(
        uint256 indexed escrowId,
        bytes32 resultHash,
        VerificationStatus status
    );

    modifier onlyOwner() {
        require(
            msg.sender == owner,
            "Only owner"
        );
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function createVerification(
        uint256 escrowId,
        address provider,
        bytes32 requestHash
    )
        external
        onlyOwner
    {
        require(
            escrowId > 0,
            "Invalid escrow ID"
        );

        require(
            provider != address(0),
            "Invalid provider"
        );

        require(
            requestHash != bytes32(0),
            "Invalid request hash"
        );

        require(
            verifications[escrowId].escrowId == 0,
            "Verification already exists"
        );

        verifications[escrowId] = Verification({
            escrowId: escrowId,
            provider: provider,
            requestHash: requestHash,
            resultHash: bytes32(0),
            status: VerificationStatus.Pending,
            verifiedAt: 0
        });

        emit ServiceVerificationCreated(
            escrowId,
            provider,
            requestHash
        );
    }

    function verifyService(
        uint256 escrowId,
        bytes32 resultHash,
        bool valid
    )
        external
        onlyOwner
    {
        Verification storage verification =
            verifications[escrowId];

        require(
            verification.escrowId != 0,
            "Verification does not exist"
        );

        require(
            verification.status ==
            VerificationStatus.Pending,
            "Already verified"
        );

        require(
            resultHash != bytes32(0),
            "Invalid result hash"
        );

        verification.resultHash = resultHash;

        if (valid) {
            verification.status =
                VerificationStatus.Valid;
        } else {
            verification.status =
                VerificationStatus.Invalid;
        }

        verification.verifiedAt =
            block.timestamp;

        emit ServiceVerified(
            escrowId,
            resultHash,
            verification.status
        );
    }

    function getVerification(
        uint256 escrowId
    )
        external
        view
        returns (Verification memory)
    {
        require(
            verifications[escrowId].escrowId != 0,
            "Verification does not exist"
        );

        return verifications[escrowId];
    }
}