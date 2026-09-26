import { expect } from "chai";
import { network } from "hardhat";

describe("Escrow Reentrancy Security", function () {

    it("should block a real reentrancy attempt", async function () {

        const { ethers } =
            await network.create();


        // ------------------------------------------------
        // 1. Deploy AgentRegistry
        // ------------------------------------------------

        const registry =
            await ethers.deployContract(
                "AgentRegistry"
            );


        // ------------------------------------------------
        // 2. Deploy Escrow
        // ------------------------------------------------

        const escrow =
            await ethers.deployContract(
                "Escrow"
            );


        // ------------------------------------------------
        // 3. Configure AgentRegistry
        // ------------------------------------------------

        await escrow.setAgentRegistry(
            await registry.getAddress()
        );


        // ------------------------------------------------
        // 4. Deploy buyer attacker
        // ------------------------------------------------

        const attacker =
            await ethers.deployContract(
                "ReentrancyAttacker",
                [
                    await escrow.getAddress(),
                    await registry.getAddress()
                ]
            );


        // ------------------------------------------------
        // 5. Deploy malicious provider
        // ------------------------------------------------

        const maliciousProvider =
            await ethers.deployContract(
                "MaliciousProvider",
                [
                    await escrow.getAddress(),
                    await registry.getAddress()
                ]
            );


        // ------------------------------------------------
        // 6. Register buyer agent
        // ------------------------------------------------

        await attacker.registerBuyerAgent(
            "BUYER-ATTACKER"
        );


        // ------------------------------------------------
        // 7. Register malicious provider
        // ------------------------------------------------

        await maliciousProvider.registerProviderAgent(
            "PROVIDER-ATTACKER"
        );


        // ------------------------------------------------
        // 8. Connect attacker and provider
        // ------------------------------------------------

        await attacker.setProvider(
            await maliciousProvider.getAddress()
        );


        await maliciousProvider.setAttacker(
            await attacker.getAddress()
        );


        // ------------------------------------------------
        // 9. Prepare escrow
        // ------------------------------------------------

        const amount =
            ethers.parseEther("0.01");


        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "reentrancy-security-test"
                )
            );


        const latestBlock =
            await ethers.provider.getBlock(
                "latest"
            );


        const deadline =
            BigInt(
                latestBlock!.timestamp
            ) + 3600n;


        // ------------------------------------------------
        // 10. Create escrow
        // ------------------------------------------------

        await attacker.createEscrow(
            "PROVIDER-ATTACKER",
            serviceHash,
            deadline,
            {
                value: amount
            }
        );


        // ------------------------------------------------
        // 11. Set target escrow
        // ------------------------------------------------

        await maliciousProvider.setTargetEscrow(
            1
        );


        // ------------------------------------------------
        // 12. Enable attack
        // ------------------------------------------------

        await maliciousProvider.enableAttack();


        // ------------------------------------------------
        // 13. Verify initial state
        // ------------------------------------------------

        const beforeData =
            await escrow.getEscrow(1);


        expect(
            beforeData.buyer
        ).to.equal(
            await attacker.getAddress()
        );


        expect(
            beforeData.provider
        ).to.equal(
            await maliciousProvider.getAddress()
        );


        expect(
            beforeData.amount
        ).to.equal(
            amount
        );


        expect(
            beforeData.status
        ).to.equal(1);


        // ------------------------------------------------
        // 14. Start the REAL attack
        //
        // Buyer
        //   ↓
        // Escrow.releaseEscrow()
        //   ↓
        // Provider receives ETH
        //   ↓
        // Provider callback
        //   ↓
        // Buyer re-enters Escrow
        //   ↓
        // nonReentrant blocks it
        // ------------------------------------------------

        await attacker.startAttack(1);


        // ------------------------------------------------
        // 15. Verify reentrancy was blocked
        // ------------------------------------------------

        expect(
            await maliciousProvider.reentrancyBlocked()
        ).to.equal(true);


        // ------------------------------------------------
        // 16. Verify escrow was released normally
        // ------------------------------------------------

        const afterData =
            await escrow.getEscrow(1);


        expect(
            afterData.status
        ).to.equal(2); // Released


        // ------------------------------------------------
        // 17. Verify Escrow balance is zero
        // ------------------------------------------------

        const escrowBalance =
            await ethers.provider.getBalance(
                await escrow.getAddress()
            );


        expect(
            escrowBalance
        ).to.equal(0);
    });
});