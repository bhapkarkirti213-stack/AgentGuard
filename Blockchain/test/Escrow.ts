import { expect } from "chai";
import { network } from "hardhat";

describe("Escrow", function () {

    async function setup() {

        const { ethers } = await network.create();

        const [buyer, provider, other] =
            await ethers.getSigners();

        const registry =
            await ethers.deployContract(
                "AgentRegistry"
            );

        await registry
            .connect(provider)
            .registerAgent(
                "WEATHER-001",
                "Weather Data"
            );

        const escrow =
            await ethers.deployContract(
                "Escrow"
            );

        await escrow.setAgentRegistry(
            await registry.getAddress()
        );

        return {
            ethers,
            buyer,
            provider,
            other,
            registry,
            escrow
        };
    }


    async function getDeadline(
        ethers: any,
        seconds: bigint
    ) {

        const latestBlock =
            await ethers.provider.getBlock(
                "latest"
            );

        return (
            BigInt(latestBlock!.timestamp) +
            seconds
        );
    }


    it("should create an escrow and lock ETH", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        const data =
            await escrow.getEscrow(1);

        expect(data.buyer)
            .to.equal(buyer.address);

        expect(data.provider)
            .to.equal(provider.address);

        expect(data.agentId)
            .to.equal("WEATHER-001");

        expect(data.amount)
            .to.equal(amount);

        expect(data.status)
            .to.equal(1);

        expect(
            await ethers.provider.getBalance(
                await escrow.getAddress()
            )
        ).to.equal(amount);
    });


    it("should release ETH to the provider", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        const balanceBefore =
            await ethers.provider.getBalance(
                provider.address
            );

        await escrow
            .connect(buyer)
            .releaseEscrow(1);

        const balanceAfter =
            await ethers.provider.getBalance(
                provider.address
            );

        expect(
            balanceAfter - balanceBefore
        ).to.equal(amount);

        const data =
            await escrow.getEscrow(1);

        expect(data.status)
            .to.equal(2);
    });


    it("should prevent a non-buyer from releasing escrow", async function () {

        const {
            ethers,
            buyer,
            provider,
            other,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        await expect(
            escrow
                .connect(other)
                .releaseEscrow(1)
        ).to.be.revertedWith(
            "Only buyer"
        );
    });


    it("should prevent releasing an escrow twice", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        await escrow
            .connect(buyer)
            .releaseEscrow(1);

        await expect(
            escrow
                .connect(buyer)
                .releaseEscrow(1)
        ).to.be.revertedWith(
            "Escrow not funded"
        );
    });


    it("should reject refund before the deadline", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        await expect(
            escrow
                .connect(buyer)
                .refundEscrow(1)
        ).to.be.revertedWith(
            "Deadline not reached"
        );
    });


    it("should refund ETH after the deadline", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                100n
            );

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

        await ethers.provider.send(
            "evm_increaseTime",
            [101]
        );

        await ethers.provider.send(
            "evm_mine"
        );

        const balanceBefore =
            await ethers.provider.getBalance(
                buyer.address
            );

        const tx =
            await escrow
                .connect(buyer)
                .refundEscrow(1);

        const receipt =
            await tx.wait();

        const balanceAfter =
            await ethers.provider.getBalance(
                buyer.address
            );

        expect(
            balanceAfter
        ).to.be.greaterThan(
            balanceBefore
        );

        const data =
            await escrow.getEscrow(1);

        expect(data.status)
            .to.equal(3);
    });


    it("should prevent a non-buyer from requesting a refund", async function () {

        const {
            ethers,
            buyer,
            provider,
            other,
            escrow
        } = await setup();

        const amount =
            ethers.parseEther("0.01");

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

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

        await expect(
            escrow
                .connect(other)
                .refundEscrow(1)
        ).to.be.revertedWith(
            "Only buyer"
        );
    });


    it("should reject zero-value escrow", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

        await expect(
            escrow
                .connect(buyer)
                .createEscrow(
                    "WEATHER-001",
                    provider.address,
                    serviceHash,
                    deadline,
                    {
                        value: 0
                    }
                )
        ).to.be.revertedWith(
            "Amount must be greater than zero"
        );
    });


    it("should reject buyer as provider", async function () {

        const {
            ethers,
            buyer,
            escrow
        } = await setup();

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

        await expect(
            escrow
                .connect(buyer)
                .createEscrow(
                    "WEATHER-001",
                    buyer.address,
                    serviceHash,
                    deadline,
                    {
                        value: ethers.parseEther("0.01")
                    }
                )
        ).to.be.revertedWith(
            "Buyer cannot be provider"
        );
    });


    it("should reject an invalid provider", async function () {

        const {
            ethers,
            buyer,
            other,
            escrow
        } = await setup();

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

        await expect(
            escrow
                .connect(buyer)
                .createEscrow(
                    "WEATHER-001",
                    other.address,
                    serviceHash,
                    deadline,
                    {
                        value: ethers.parseEther("0.01")
                    }
                )
        ).to.be.revertedWith(
            "Provider mismatch"
        );
    });


    it("should reject an expired deadline", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

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

        const expiredDeadline =
            BigInt(latestBlock!.timestamp) - 1n;

        await expect(
            escrow
                .connect(buyer)
                .createEscrow(
                    "WEATHER-001",
                    provider.address,
                    serviceHash,
                    expiredDeadline,
                    {
                        value: ethers.parseEther("0.01")
                    }
                )
        ).to.be.revertedWith(
            "Invalid deadline"
        );
    });


    it("should track the number of escrows", async function () {

        const {
            ethers,
            buyer,
            provider,
            escrow
        } = await setup();

        const serviceHash =
            ethers.keccak256(
                ethers.toUtf8Bytes(
                    "weather-service"
                )
            );

        const deadline =
            await getDeadline(
                ethers,
                3600n
            );

        await escrow
            .connect(buyer)
            .createEscrow(
                "WEATHER-001",
                provider.address,
                serviceHash,
                deadline,
                {
                    value: ethers.parseEther("0.01")
                }
            );

        expect(
            await escrow.getEscrowCount()
        ).to.equal(1);
    });
});