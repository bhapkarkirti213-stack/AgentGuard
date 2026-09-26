import { expect } from "chai";
import { network } from "hardhat";

describe("Escrow + Reputation Integration", function () {

    it("should update provider reputation after successful escrow", async function () {

        const { ethers } = await network.create();

        const [buyer, provider] =
            await ethers.getSigners();

        // Deploy AgentRegistry
        const registry =
            await ethers.deployContract(
                "AgentRegistry"
            );

        // Register provider
        await registry
            .connect(provider)
            .registerAgent(
                "WEATHER-001",
                "Weather Data"
            );

        // Deploy Reputation
        const reputation =
            await ethers.deployContract(
                "Reputation"
            );

        // Deploy Escrow
        const escrow =
            await ethers.deployContract(
                "Escrow"
            );

        // Configure AgentRegistry
        await escrow.setAgentRegistry(
            await registry.getAddress()
        );

        // Authorize Escrow as Reputation updater
        await reputation.setAuthorizedUpdater(
            await escrow.getAddress(),
            true
        );

        // Configure Reputation
        await escrow.setReputationContract(
            await reputation.getAddress()
        );

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const latestBlock =
            await ethers.provider.getBlock(
                "latest"
            );

        const deadline =
            BigInt(latestBlock!.timestamp) +
            3600n;

        // Create escrow
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

        // Check initial reputation
        const before =
            await reputation.getReputation(
                provider.address
            );

        expect(
            before.successfulTransactions
        ).to.equal(0);

        expect(
            before.totalTransactionValue
        ).to.equal(0);

        // Release escrow
        await escrow
            .connect(buyer)
            .releaseEscrow(1);

        // Check updated reputation
        const after =
            await reputation.getReputation(
                provider.address
            );

        expect(
            after.successfulTransactions
        ).to.equal(1);

        expect(
            after.failedTransactions
        ).to.equal(0);

        expect(
            after.totalTransactionValue
        ).to.equal(amount);

        expect(
            after.successfulTransactionValue
        ).to.equal(amount);

        expect(
            await reputation.getReputationScore(
                provider.address
            )
        ).to.equal(100);
    });
});