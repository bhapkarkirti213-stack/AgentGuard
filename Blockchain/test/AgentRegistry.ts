import { expect } from "chai";
import { network } from "hardhat";

describe("AgentRegistry", function () {

    it("should register an agent correctly", async function () {

        const { ethers } = await network.create();

        const [owner] = await ethers.getSigners();

        const registry = await ethers.deployContract("AgentRegistry");

        await registry.registerAgent(
            "WEATHER-001",
            "Weather Data"
        );

        const agent = await registry.getAgent("WEATHER-001");

        expect(agent[0]).to.equal("WEATHER-001");
        expect(agent[1]).to.equal(owner.address);
        expect(agent[2]).to.equal("Weather Data");
        expect(agent[3]).to.equal(true);
    });
});