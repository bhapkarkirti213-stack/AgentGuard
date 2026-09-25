import { network } from "hardhat";

async function main() {
    const { ethers } = await network.create();

    const [signer] = await ethers.getSigners();
    const address = await signer.getAddress();

    const net = await ethers.provider.getNetwork();
    const balance = await ethers.provider.getBalance(address);

    console.log("Wallet:", address);
    console.log("Chain ID:", net.chainId.toString());
    console.log("Balance:", ethers.formatEther(balance), "ETH");

    console.log("Deploying AgentRegistry...");

    const registry = await ethers.deployContract("AgentRegistry");

    await registry.waitForDeployment();

    console.log("AgentRegistry deployed to:");
    console.log(await registry.getAddress());
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});