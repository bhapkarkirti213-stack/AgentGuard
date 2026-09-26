import { expect } from "chai";
import { network } from "hardhat";

describe("Reputation", function () {

    it("should start with zero reputation", async function () {

        const { ethers } = await network.create();

        const [agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        const data = await reputation.getReputation(agent.address);
        const score = await reputation.getReputationScore(agent.address);

        expect(data.successfulTransactions).to.equal(0);
        expect(data.failedTransactions).to.equal(0);
        expect(data.refundedTransactions).to.equal(0);
        expect(data.disputes).to.equal(0);

        expect(score).to.equal(0);
    });


    it("should increase reputation after a successful transaction", async function () {

        const { ethers } = await network.create();

        const [owner, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        const score = await reputation.getReputationScore(
            agent.address
        );

        expect(score).to.equal(100);
    });


    it("should calculate reputation using successful and failed transactions", async function () {

        const { ethers } = await network.create();

        const [owner, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        await reputation.recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        await reputation.recordFailure(
            agent.address,
            ethers.parseEther("0.01")
        );

        const score = await reputation.getReputationScore(
            agent.address
        );

        expect(score).to.equal(79);
    });


    it("should record refunds", async function () {

        const { ethers } = await network.create();

        const [owner, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        await reputation.recordRefund(agent.address);

        const data = await reputation.getReputation(
            agent.address
        );

        expect(data.successfulTransactions).to.equal(1);
        expect(data.refundedTransactions).to.equal(1);
    });


    it("should record disputes", async function () {

        const { ethers } = await network.create();

        const [owner, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        await reputation.recordDispute(agent.address);

        const data = await reputation.getReputation(
            agent.address
        );

        expect(data.successfulTransactions).to.equal(1);
        expect(data.disputes).to.equal(1);
    });


    it("should store transaction values", async function () {

        const { ethers } = await network.create();

        const [owner, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        const value = ethers.parseEther("0.05");

        await reputation.recordSuccess(
            agent.address,
            value
        );

        const data = await reputation.getReputation(
            agent.address
        );

        expect(data.totalTransactionValue).to.equal(value);
        expect(data.successfulTransactionValue).to.equal(value);
    });


    it("should allow the owner to authorize an updater", async function () {

        const { ethers } = await network.create();

        const [owner, updater] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.setAuthorizedUpdater(
            updater.address,
            true
        );

        expect(
            await reputation.authorizedUpdaters(updater.address)
        ).to.equal(true);
    });


    it("should reject unauthorized reputation updates", async function () {

        const { ethers } = await network.create();

        const [owner, attacker] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await expect(
            reputation.connect(attacker).recordSuccess(
                attacker.address,
                ethers.parseEther("0.01")
            )
        ).to.be.revertedWith(
            "Not authorized updater"
        );
    });


    it("should allow an authorized updater to record a transaction", async function () {

        const { ethers } = await network.create();

        const [owner, updater, agent] = await ethers.getSigners();

        const reputation = await ethers.deployContract("Reputation");

        await reputation.setAuthorizedUpdater(
            updater.address,
            true
        );

        await reputation.connect(updater).recordSuccess(
            agent.address,
            ethers.parseEther("0.01")
        );

        const score =
            await reputation.getReputationScore(agent.address);

        expect(score).to.equal(100);
    });

});