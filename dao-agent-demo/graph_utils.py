
import os

from time import sleep
from datetime import datetime, timezone
from typing import List, Dict, Optional

from subgrounds import Subgrounds

from dotenv import load_dotenv

load_dotenv()

from constants_utils import (
    DAOHAUS_GRAPH_URLS
    )

TARGET_CHAIN = os.getenv("TARGET_CHAIN", "0x2105")
GRAPH_URL = "https://gateway-arbitrum.network.thegraph.com/api/" + os.getenv("GRAPH_KEY", "nokey") + DAOHAUS_GRAPH_URLS[TARGET_CHAIN]


class DaohausGraphData:
    def __init__(self):
        """
        Initialize daohaus graph data
        python subgrounds https://thegraph.com/docs/en/querying/querying-with-python/
        """
        print("initializing graph data")
        if not os.getenv("GRAPH_KEY") or not os.getenv("TARGET_DAO"):
            raise ValueError("GRAPH_KEY and TARGET_DAO must be set in the .env file")

        self.sg = Subgrounds()

        # Load the subgraph
        self.dh_v3 = self.sg.load_subgraph(GRAPH_URL)

        self.dao_id = os.getenv("TARGET_DAO")

        self.dao  = self.dh_v3.Query.daos(
                where={"id": self.dao_id},
            )

        self.daoRecords = self.dao.records(
                first=1,
                orderBy="createdAt",
                where={ "table": "daoProfile" }
            )

    def get_dao_data(self) -> str:
        """
        Get DAO data
        Args:
            dao_id (str): The DAO ID
        Returns:
            str: DAO data
        """
        try:
            # Construct the query

            result = self.sg.query_df([
                self.dao.createdAt,
                self.dao.createdBy,
                self.dao.contentType,
                self.dao.content,
            ])

            return result.to_json()
        except Exception as e:
            return f"Error getting DAO data: {str(e)}"
        
    def get_passed_proposals_data(self) -> str:
        """
        Get proposals data of proposals that have passed
        Args:
            None
        Returns:
            str: Proposals data
        """
        try:
            # Current time in UTC as a synthetic field
            now = datetime.now(timezone.utc).timestamp()

            # Define a synthetic field for ageInSeconds
            proposal = self.dh_v3.Proposal  # Assuming Proposal is an entity in the schema
            proposal.ageInSeconds = now - proposal.createdAt
            proposal.displayYesBalance = proposal.yesBalance / 10**18
            proposal.displayNoBalance = proposal.noBalance / 10**18
            # Construct the query
            proposals = self.dh_v3.Query.proposals(
                first=20,
                orderBy="createdAt",
                orderDirection="desc",
                where={"dao": self.dao_id, "passed": True},
            )


            result = self.sg.query_df([
                proposals.proposalId,
                proposals.ageInSeconds,  # Use synthetic field as a regular field
                proposals.yesVotes,
                proposals.noVotes,
                proposals.createdAt,
                proposals.details,
                proposals.graceEnds,
                proposals.passed,
                proposals.displayYesBalance,
                proposals.displayNoBalance,
            ])
            return result.to_json()

        except Exception as e:
            return f"Error getting proposals data: {str(e)}"
        
    def get_proposals_data(self) -> str:
        """
        Get proposals data
        Args:
            None
        Returns:
            str: Proposals data frame
        """
        try:
            # Current time in UTC as a synthetic field
            now = datetime.now(timezone.utc).timestamp()

            # Define a synthetic field for ageInSeconds
            proposal = self.dh_v3.Proposal  # Assuming Proposal is an entity in the schema
            proposal.ageInSeconds = now - proposal.createdAt
            proposal.displayYesBalance = proposal.yesBalance / 10**18
            proposal.displayNoBalance = proposal.noBalance / 10**18
            # Construct the query
            proposals = self.dh_v3.Query.proposals(
                first=10,
                orderBy="createdAt",
                orderDirection="desc",
                where={"dao": self.dao_id},
            )


            result = self.sg.query_df([
                proposals.proposalId,
                proposals.ageInSeconds,  # Use synthetic field as a regular field
                proposals.yesVotes,
                proposals.noVotes,
                proposals.createdAt,
                proposals.details,
                proposals.graceEnds,
                proposals.passed,
                proposals.displayYesBalance,
                proposals.displayNoBalance,
            ])

            return result.to_json()

        except Exception as e:
            return f"Error getting proposals data: {str(e)}"
    
    def get_proposal_data(self, proposal_id: str) -> str:
        """
        Get proposal data
        Args:
            proposal_id (str): The proposal ID
        Returns:
            str: Proposal data
        """
        try:
            # Current time in UTC as a synthetic field
            now = datetime.now(timezone.utc).timestamp()

            # Define a synthetic field for ageInSeconds
            proposal = self.dh_v3.Proposal  # Assuming Proposal is an entity in the schema
            proposal.ageInSeconds = now - proposal.createdAt
            proposal.displayYesBalance = proposal.yesBalance / 10**18
            proposal.displayNoBalance = proposal.noBalance / 10**18

            # Construct the query
            proposal = self.dh_v3.Query.proposals(
                where={"proposalId": proposal_id, "dao": self.dao_id},
            )

            result = self.sg.query_df([
                proposal.proposalId,
                proposal.ageInSeconds,  # Use synthetic field as a regular field
                proposal.yesVotes,
                proposal.noVotes,
                proposal.createdAt,
                proposal.details,
                # proposal.votes, # This is a list of votes, TODO: Figure out how to query this
                proposal.graceEnds,
                proposal.passed,
                proposal.displayYesBalance,
                proposal.displayNoBalance
            ])

            # Add a proposal URL
            result["proposalUrl"] = self.create_dh_proposal_url(proposal.proposalId)

            return result.to_json()
        except Exception as e:
            return f"Error getting proposal data: {str(e)}"
        
    def get_proposal_votes_data(self, proposal_id: int) -> str:
        """
        Get proposal votes data
        Args:
            proposal_id (int): The proposal ID
        Returns:
            str: Proposal votes data
        """
        try:
            # Define a synthetic field for ageInSeconds
            vote = self.dh_v3.Vote  # Assuming Proposal is an entity in the schema
            vote.displayBalance = vote.balance / 10**18
            # Construct the query
            votes = self.dh_v3.Query.votes(
                where=[
                    vote.proposal.proposalId == proposal_id,
                    vote.daoAddress == self.dao_id,],
            )

            result = self.sg.query_df([
                votes.createdAt,
                votes.balance,
                votes.approved,
                votes.member.memberAddress,
                votes.displayBalance,
            ])

            return result.to_json()
        except Exception as e:
            return f"Error getting proposal votes data: {str(e)}"
    
    def get_proposal_count(self) -> str:
        """
        Get proposal count
        Args:
            None
        Returns:
            str: Proposal count
        """
        try:
            # Construct the query

            result = self.sg.query_df([
                self.dao.proposalCount,
            ])

            return result.to_json()
        except Exception as e:
            return f"Error getting proposal count: {str(e)}"
        
    def create_dh_proposal_url(self, proposal_id: str) -> str:
        """
        Create a proposal URL
        Args:
            proposal_id (str): The proposal ID
        Returns:
            str: The URL
        """
        return f"https://admin.daohaus.fun/#/molochV3/{TARGET_CHAIN}/{self.dao_id}/proposal/{proposal_id}"
        