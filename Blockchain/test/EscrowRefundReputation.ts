import { expect } from "chai";
import { network } from "hardhat";

describe("Escrow + Refund + Reputation Integration", function () {

    it("should update provider reputation after escrow refund", async function () {

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
                    "weather-service-failure"
                )
            );

        const latestBlock =
            await ethers.provider.getBlock(
                "latest"
            );

        const deadline =
            BigInt(latestBlock!.timestamp) +
            100n;

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
            before.failedTransactions
        ).to.equal(0);

        expect(
            before.refundedTransactions
        ).to.equal(0);

        // Move blockchain time beyond deadline
        await ethers.provider.send(
            "evm_increaseTime",
            [101]
        );

        await ethers.provider.send(
            "evm_mine"
        );

        // Refund escrow
        await escrow
            .connect(buyer)
            .refundEscrow(1);

        // Check updated reputation
        const after =
            await reputation.getReputation(
                provider.address
            );

        expect(
            after.successfulTransactions
        ).to.equal(0);

        expect(
            after.failedTransactions
        ).to.equal(1);

        expect(
            after.refundedTransactions
        ).to.equal(1);

        expect(
            after.totalTransactionValue
        ).to.equal(amount);

        expect(
            after.successfulTransactionValue
        ).to.equal(0);

        // Current experimental formula
        // gives a score of 15.
        expect(
            await reputation.getReputationScore(
                provider.address
            )
        ).to.equal(15);
    });
});