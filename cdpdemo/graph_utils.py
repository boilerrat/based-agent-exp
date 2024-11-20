
import os

from time import sleep
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import uuid

from subgrounds import Subgrounds
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

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
        self.dh_v3 = self.sg.load_subgraph(
            "https://gateway-arbitrum.network.thegraph.com/api/" + os.getenv("GRAPH_KEY") + "/subgraphs/id/7yh4eHJ4qpHEiLPAk9BXhL5YgYrTrRE6gWy8x4oHyAqW"
        )

        self.dao_id = os.getenv("TARGET_DAO")

        self.dao  = self.dh_v3.Query.daos(
                where={"id": self.dao_id},
            )

        self.daoRecords = self.dao.records(
                first=1,
                orderBy="createdAt",
                where={ "table": "daoProfile" }
            )

    def get_dao_data(self) -> Dict:
        """
        Get DAO data
        Args:
            dao_id (str): The DAO ID
        Returns:
            Dict: DAO data
        """
        try:
            # Construct the query

            result = self.sg.query([
                self.dao.createdAt,
                self.dao.createdBy,
                self.dao.contentType,
                self.dao.content,
            ])

            return result
        except Exception as e:
            return f"Error getting DAO data: {str(e)}"
        
    def get_proposals_data(self) -> Dict:
        """
        Get proposals data
        Args:
            None
        Returns:
            Dict: Proposals data
        """
        try:
            # Current time in UTC as a synthetic field
            now = datetime.now(timezone.utc).timestamp()

            # Define a synthetic field for age
            proposal = self.dh_v3.Proposal  # Assuming Proposal is an entity in the schema
            proposal.age = now - proposal.createdAt
            # Construct the query
            proposals = self.dh_v3.Query.proposals(
                first=10,
                orderBy="createdAt",
                orderDirection="desc",
                where={"dao": self.dao_id},
            )


            result = self.sg.query([
                proposals.proposalId,
                proposals.yesVotes,
                proposals.noVotes,
                proposals.yesBalance,
                proposals.noBalance,
                proposals.createdAt,
                proposals.details,
                proposals.votes,
                proposals.age,  # Use synthetic field as a regular field
            ])

            print("type of result", type(result))

            return result

        except Exception as e:
            return f"Error getting proposals data: {str(e)}"
        
    def get_proposal_data(self, proposal_id: str) -> Dict:
        """
        Get proposal data
        Args:
            proposal_id (str): The proposal ID
        Returns:
            Dict: Proposal data
        """
        try:
            # Construct the query
            proposal = self.dh_v3.Query.proposals(
                where={"proposalId": proposal_id, "dao": self.dao_id},
            )

            result = self.sg.query([
                proposal.yesVotes,
                proposal.noVotes,
                proposal.yesBalance,
                proposal.noBalance,
                proposal.createdAt,
                proposal.details,
                proposal.votes
            ])

            return result
        except Exception as e:
            return f"Error getting proposal data: {str(e)}"
        

    def get_proposal_count(self) -> Dict:
        """
        Get proposal count
        Args:
            None
        Returns:
            Dict: Proposal count
        """
        try:
            # Construct the query

            result = self.sg.query([
                self.dao.proposalCount,
            ])

            return result
        except Exception as e:
            return f"Error getting proposal count: {str(e)}"
        