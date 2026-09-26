import { expect } from "chai";
import { network } from "hardhat";

describe("Escrow + ServiceVerifier Integration", function () {

    async function setup() {

        const { ethers } = await network.create();

        const [
            owner,
            buyer,
            provider,
            other
        ] = await ethers.getSigners();

        // Deploy Registry
        const registry =
            await ethers.deployContract("AgentRegistry");

        // Register provider
        await registry
            .connect(provider)
            .registerAgent(
                "WEATHER-001",
                "Weather Data"
            );

        // Deploy Reputation
        const reputation =
            await ethers.deployContract("Reputation");

        // Deploy ServiceVerifier
        const verifier =
            await ethers.deployContract("ServiceVerifier");

        // Deploy Escrow
        const escrow =
            await ethers.deployContract("Escrow");

        // Configure Escrow
        await escrow.setAgentRegistry(
            await registry.getAddress()
        );

        await escrow.setReputationContract(
            await reputation.getAddress()
        );

        await escrow.setServiceVerifier(
            await verifier.getAddress()
        );

        // Authorize Escrow to update reputation
        await reputation.setAuthorizedUpdater(
            await escrow.getAddress(),
            true
        );

        return {
            ethers,
            owner,
            buyer,
            provider,
            other,
            registry,
            reputation,
            verifier,
            escrow
        };
    }


    async function createEscrow(system: any) {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = system;

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-request-pune"
                )
            );

        const latestBlock =
            await ethers.provider.getBlock("latest");

        const deadline =
            BigInt(latestBlock!.timestamp) + 3600n;

        await escrow
            .connect(buyer)
            .createEscrow(
                "WEATHER-001",
                provider.address,
                serviceHash,
                deadline,
                {
                    value: amount
                }
            );

        return {
            amount,
            serviceHash
        };
    }


    it("should release payment for a valid verified service",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow,
                reputation
            } = system;

            const {
                amount,
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "weather-result-pune-28.4"
                    )
                );

            // Create verification
            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            // Mark service valid
            await verifier.verifyService(
                1,
                resultHash,
                true
            );

            const providerBefore =
                await ethers.provider.getBalance(
                    provider.address
                );

            // Release payment
            await escrow
                .connect(buyer)
                .releaseVerifiedEscrow(1);

            const providerAfter =
                await ethers.provider.getBalance(
                    provider.address
                );

            expect(
                providerAfter - providerBefore
            ).to.equal(amount);

            const escrowData =
                await escrow.getEscrow(1);

            expect(
                escrowData.status
            ).to.equal(2);

            // Check reputation
            const reputationData =
                await reputation.getReputation(
                    provider.address
                );

            expect(
                reputationData.successfulTransactions
            ).to.equal(1);

            expect(
                reputationData.successfulTransactionValue
            ).to.equal(amount);

            expect(
                await reputation.getReputationScore(
                    provider.address
                )
            ).to.equal(100);
        });


    it("should refund payment for an invalid verified service",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow,
                reputation
            } = system;

            const {
                amount,
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "invalid-weather-result"
                    )
                );

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            // Mark service invalid
            await verifier.verifyService(
                1,
                resultHash,
                false
            );

            await escrow
                .connect(buyer)
                .refundVerifiedEscrow(1);

            const escrowBalance =
                await ethers.provider.getBalance(
                    await escrow.getAddress()
                );

            expect(
                escrowBalance
            ).to.equal(0);

            const escrowData =
                await escrow.getEscrow(1);

            expect(
                escrowData.status
            ).to.equal(3);

            // Check reputation
            const reputationData =
                await reputation.getReputation(
                    provider.address
                );

            expect(
                reputationData.failedTransactions
            ).to.equal(1);

            expect(
                reputationData.refundedTransactions
            ).to.equal(1);

            expect(
                reputationData.totalTransactionValue
            ).to.equal(amount);
        });


    it("should reject release while verification is pending",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await expect(
                escrow
                    .connect(buyer)
                    .releaseVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Service not verified"
            );
        });


    it("should reject refund while verification is pending",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await expect(
                escrow
                    .connect(buyer)
                    .refundVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Service not invalid"
            );
        });


    it("should reject verification with the wrong provider",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                other,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "weather-result"
                    )
                );

            // Deliberately use wrong provider
            await verifier.createVerification(
                1,
                other.address,
                serviceHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                true
            );

            await expect(
                escrow
                    .connect(buyer)
                    .releaseVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Provider mismatch"
            );
        });


    it("should reject release by a non-buyer",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                other,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "weather-result"
                    )
                );

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                true
            );

            await expect(
                escrow
                    .connect(other)
                    .releaseVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Only buyer"
            );
        });


    it("should reject refund by a non-buyer",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                other,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "invalid-weather-result"
                    )
                );

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                false
            );

            await expect(
                escrow
                    .connect(other)
                    .refundVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Only buyer"
            );
        });


    it("should prevent releasing an already released escrow",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "weather-result"
                    )
                );

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                true
            );

            await escrow
                .connect(buyer)
                .releaseVerifiedEscrow(1);

            await expect(
                escrow
                    .connect(buyer)
                    .releaseVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Escrow not funded"
            );
        });


    it("should prevent refunding an already refunded escrow",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const resultHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "invalid-weather-result"
                    )
                );

            await verifier.createVerification(
                1,
                provider.address,
                serviceHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                false
            );

            await escrow
                .connect(buyer)
                .refundVerifiedEscrow(1);

            await expect(
                escrow
                    .connect(buyer)
                    .refundVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Escrow not funded"
            );
        });
    it(
        "should reject verification when request hash does not match escrow service hash",
        async function () {

            const system = await setup();

            const {
                ethers,
                buyer,
                provider,
                verifier,
                escrow
            } = system;

            const {
                serviceHash
            } = await createEscrow(system);

            const wrongRequestHash =
                ethers.keccak256(
                    ethers.toUtf8Bytes(
                        "different-weather-request"
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
                wrongRequestHash
            );

            await verifier.verifyService(
                1,
                resultHash,
                true
            );

            await expect(
                escrow
                    .connect(buyer)
                    .releaseVerifiedEscrow(1)
            ).to.be.revertedWith(
                "Request hash mismatch"
            );
        }
    );

});