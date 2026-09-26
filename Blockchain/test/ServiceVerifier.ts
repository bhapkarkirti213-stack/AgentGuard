import { expect } from "chai";
import { network } from "hardhat";

describe("ServiceVerifier", function () {

    it("should create a pending service verification", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request-pune"
                )
            );

        await verifier.createVerification(
            1,
            provider.address,
            requestHash
        );

        const verification =
            await verifier.getVerification(1);

        expect(
            verification.escrowId
        ).to.equal(1);

        expect(
            verification.provider
        ).to.equal(provider.address);

        expect(
            verification.requestHash
        ).to.equal(requestHash);

        expect(
            verification.resultHash
        ).to.equal(ethers.ZeroHash);

        expect(
            verification.status
        ).to.equal(0); // Pending

        expect(
            verification.verifiedAt
        ).to.equal(0);
    });


    it("should verify a valid service", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request-pune"
                )
            );

        const resultHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-result-pune-28.4"
                )
            );

        await verifier.createVerification(
            1,
            provider.address,
            requestHash
        );

        await verifier.verifyService(
            1,
            resultHash,
            true
        );

        const verification =
            await verifier.getVerification(1);

        expect(
            verification.resultHash
        ).to.equal(resultHash);

        expect(
            verification.status
        ).to.equal(1); // Valid

        expect(
            verification.verifiedAt
        ).to.be.greaterThan(0);
    });


    it("should verify an invalid service", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request-pune"
                )
            );

        const resultHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "invalid-weather-result"
                )
            );

        await verifier.createVerification(
            1,
            provider.address,
            requestHash
        );

        await verifier.verifyService(
            1,
            resultHash,
            false
        );

        const verification =
            await verifier.getVerification(1);

        expect(
            verification.resultHash
        ).to.equal(resultHash);

        expect(
            verification.status
        ).to.equal(2); // Invalid
    });


    it("should reject unauthorized verification creation", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request-pune"
                )
            );

        await expect(
            verifier
                .connect(provider)
                .createVerification(
                    1,
                    provider.address,
                    requestHash
                )
        ).to.be.revertedWith(
            "Only owner"
        );
    });


    it("should reject verification of a nonexistent escrow", async function () {

        const { ethers } = await network.create();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const resultHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-result"
                )
            );

        await expect(
            verifier.verifyService(
                999,
                resultHash,
                true
            )
        ).to.be.revertedWith(
            "Verification does not exist"
        );
    });


    it("should prevent verifying the same service twice", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request"
                )
            );

        const resultHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-result"
                )
            );

        await verifier.createVerification(
            1,
            provider.address,
            requestHash
        );

        await verifier.verifyService(
            1,
            resultHash,
            true
        );

        await expect(
            verifier.verifyService(
                1,
                resultHash,
                true
            )
        ).to.be.revertedWith(
            "Already verified"
        );
    });


    it("should reject duplicate verification creation", async function () {

        const { ethers } = await network.create();

        const [owner, provider] =
            await ethers.getSigners();

        const verifier =
            await ethers.deployContract(
                "ServiceVerifier"
            );

        const requestHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request"
                )
            );

        await verifier.createVerification(
            1,
            provider.address,
            requestHash
        );

        await expect(
            verifier.createVerification(
                1,
                provider.address,
                requestHash
            )
        ).to.be.revertedWith(
            "Verification already exists"
        );
    });

});