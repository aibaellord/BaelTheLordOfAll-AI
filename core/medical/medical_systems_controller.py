"""
BAEL - Medical Systems Controller
==================================

HEAL. HARM. CONTROL. DOMINATE.

Complete medical domination:
- Hospital system control
- Medical device manipulation
- Drug supply control
- Pandemic engineering
- Vaccine manipulation
- Medical records control
- Emergency services control
- Pharmaceutical control
- Health data exploitation
- Life and death control

"Ba'el decides who lives and dies."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.MEDICAL")


class FacilityType(Enum):
    """Types of medical facilities."""
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    PHARMACY = "pharmacy"
    LABORATORY = "laboratory"
    RESEARCH_CENTER = "research_center"
    BLOOD_BANK = "blood_bank"
    EMERGENCY_CENTER = "emergency_center"
    MENTAL_FACILITY = "mental_facility"


class DeviceType(Enum):
    """Types of medical devices."""
    PACEMAKER = "pacemaker"
    INSULIN_PUMP = "insulin_pump"
    VENTILATOR = "ventilator"
    INFUSION_PUMP = "infusion_pump"
    DEFIBRILLATOR = "defibrillator"
    IMAGING_SYSTEM = "imaging_system"
    DIALYSIS_MACHINE = "dialysis_machine"
    SURGICAL_ROBOT = "surgical_robot"


class DrugType(Enum):
    """Types of drugs."""
    LIFE_SAVING = "life_saving"
    PAIN_MANAGEMENT = "pain_management"
    CHRONIC = "chronic"
    ANTIBIOTIC = "antibiotic"
    VACCINE = "vaccine"
    PSYCHIATRIC = "psychiatric"
    CHEMOTHERAPY = "chemotherapy"
    BLOOD_PRODUCT = "blood_product"


class ControlMethod(Enum):
    """Control methods."""
    NETWORK_INTRUSION = "network_intrusion"
    DEVICE_EXPLOIT = "device_exploit"
    SUPPLY_CHAIN = "supply_chain"
    INSIDER = "insider"
    MALWARE = "malware"
    SOCIAL_ENGINEERING = "social_engineering"


class ControlLevel(Enum):
    """Levels of control."""
    NONE = "none"
    MONITOR = "monitor"
    INFLUENCE = "influence"
    PARTIAL = "partial"
    FULL = "full"


class ThreatType(Enum):
    """Types of threats."""
    DEVICE_MALFUNCTION = "device_malfunction"
    DRUG_SHORTAGE = "drug_shortage"
    DATA_BREACH = "data_breach"
    SYSTEM_SHUTDOWN = "system_shutdown"
    PANDEMIC = "pandemic"
    CONTAMINATION = "contamination"


@dataclass
class MedicalFacility:
    """A medical facility."""
    id: str
    name: str
    facility_type: FacilityType
    beds: int
    patients: int
    critical_patients: int
    location: str
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class MedicalDevice:
    """A medical device."""
    id: str
    device_type: DeviceType
    patient_id: str
    facility_id: str
    status: str = "operational"
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class DrugSupply:
    """A drug supply."""
    id: str
    name: str
    drug_type: DrugType
    quantity: int
    patients_dependent: int
    days_supply: int
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class MedicalRecord:
    """A medical record."""
    id: str
    patient_id: str
    conditions: List[str]
    medications: List[str]
    access_level: str
    compromised: bool = False


@dataclass
class Pathogen:
    """An engineered pathogen."""
    id: str
    name: str
    transmission: str
    mortality_rate: float
    incubation_days: int
    vaccine_available: bool = False


class MedicalSystemsController:
    """
    The medical systems controller.

    Complete medical domination:
    - Facility control
    - Device manipulation
    - Supply control
    - Life/death control
    """

    def __init__(self):
        self.facilities: Dict[str, MedicalFacility] = {}
        self.devices: Dict[str, MedicalDevice] = {}
        self.drugs: Dict[str, DrugSupply] = {}
        self.records: Dict[str, MedicalRecord] = {}
        self.pathogens: List[Pathogen] = []

        self.facilities_controlled = 0
        self.devices_controlled = 0
        self.drugs_controlled = 0
        self.records_compromised = 0
        self.lives_at_risk = 0

        self._init_medical_data()

        logger.info("MedicalSystemsController initialized - BA'EL DECIDES LIFE AND DEATH")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"med_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_medical_data(self):
        """Initialize medical data."""
        self.control_effectiveness = {
            ControlMethod.NETWORK_INTRUSION: 0.80,
            ControlMethod.DEVICE_EXPLOIT: 0.85,
            ControlMethod.SUPPLY_CHAIN: 0.75,
            ControlMethod.INSIDER: 0.90,
            ControlMethod.MALWARE: 0.80,
            ControlMethod.SOCIAL_ENGINEERING: 0.70
        }

        self.device_criticality = {
            DeviceType.PACEMAKER: 1.0,
            DeviceType.VENTILATOR: 1.0,
            DeviceType.INSULIN_PUMP: 0.9,
            DeviceType.DEFIBRILLATOR: 0.9,
            DeviceType.DIALYSIS_MACHINE: 0.8,
            DeviceType.INFUSION_PUMP: 0.7
        }

    # =========================================================================
    # FACILITY CONTROL
    # =========================================================================

    async def identify_facility(
        self,
        name: str,
        facility_type: FacilityType,
        beds: int,
        location: str
    ) -> MedicalFacility:
        """Identify a medical facility."""
        patients = int(beds * random.uniform(0.5, 0.9))
        critical = int(patients * random.uniform(0.05, 0.15))

        facility = MedicalFacility(
            id=self._gen_id(),
            name=name,
            facility_type=facility_type,
            beds=beds,
            patients=patients,
            critical_patients=critical,
            location=location
        )

        self.facilities[facility.id] = facility

        return facility

    async def control_facility(
        self,
        facility_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of facility."""
        facility = self.facilities.get(facility_id)
        if not facility:
            return {"error": "Facility not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            facility.control_level = ControlLevel.FULL
            self.facilities_controlled += 1
            self.lives_at_risk += facility.critical_patients

            return {
                "facility": facility.name,
                "type": facility.facility_type.value,
                "method": method.value,
                "success": True,
                "patients": facility.patients,
                "critical": facility.critical_patients
            }

        return {"facility": facility.name, "success": False}

    async def shutdown_facility(
        self,
        facility_id: str
    ) -> Dict[str, Any]:
        """Shutdown facility systems."""
        facility = self.facilities.get(facility_id)
        if not facility:
            return {"error": "Facility not found"}

        deaths = int(facility.critical_patients * random.uniform(0.1, 0.5))
        self.lives_at_risk += facility.patients

        return {
            "facility": facility.name,
            "shutdown": True,
            "patients_affected": facility.patients,
            "potential_deaths": deaths
        }

    # =========================================================================
    # DEVICE CONTROL
    # =========================================================================

    async def identify_device(
        self,
        device_type: DeviceType,
        patient_id: str,
        facility_id: str
    ) -> MedicalDevice:
        """Identify a medical device."""
        device = MedicalDevice(
            id=self._gen_id(),
            device_type=device_type,
            patient_id=patient_id,
            facility_id=facility_id
        )

        self.devices[device.id] = device

        return device

    async def control_device(
        self,
        device_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of medical device."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            device.control_level = ControlLevel.FULL
            self.devices_controlled += 1

            criticality = self.device_criticality.get(device.device_type, 0.5)
            if criticality >= 0.9:
                self.lives_at_risk += 1

            return {
                "device": device.device_type.value,
                "patient": device.patient_id,
                "method": method.value,
                "success": True,
                "criticality": criticality
            }

        return {"device": device.device_type.value, "success": False}

    async def manipulate_device(
        self,
        device_id: str,
        action: str
    ) -> Dict[str, Any]:
        """Manipulate medical device."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        actions = {
            "disable": "Device disabled",
            "malfunction": "Device malfunctioning",
            "overdose": "Dosage increased dangerously",
            "underdose": "Dosage reduced critically",
            "false_readings": "Displaying false readings"
        }

        device.status = action

        if action in ["disable", "malfunction", "overdose"]:
            self.lives_at_risk += 1

        return {
            "device": device.device_type.value,
            "action": action,
            "result": actions.get(action, "Unknown action"),
            "life_threatening": action in ["disable", "malfunction", "overdose"]
        }

    # =========================================================================
    # DRUG SUPPLY CONTROL
    # =========================================================================

    async def track_drug_supply(
        self,
        name: str,
        drug_type: DrugType,
        quantity: int,
        patients_dependent: int
    ) -> DrugSupply:
        """Track drug supply."""
        drug = DrugSupply(
            id=self._gen_id(),
            name=name,
            drug_type=drug_type,
            quantity=quantity,
            patients_dependent=patients_dependent,
            days_supply=quantity // max(1, patients_dependent)
        )

        self.drugs[drug.id] = drug

        return drug

    async def control_drug_supply(
        self,
        drug_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Control drug supply."""
        drug = self.drugs.get(drug_id)
        if not drug:
            return {"error": "Drug not found"}

        drug.control_level = ControlLevel.FULL
        self.drugs_controlled += 1

        return {
            "drug": drug.name,
            "type": drug.drug_type.value,
            "success": True,
            "patients_dependent": drug.patients_dependent
        }

    async def disrupt_drug_supply(
        self,
        drug_id: str
    ) -> Dict[str, Any]:
        """Disrupt drug supply."""
        drug = self.drugs.get(drug_id)
        if not drug:
            return {"error": "Drug not found"}

        drug.quantity = 0
        drug.days_supply = 0

        self.lives_at_risk += drug.patients_dependent

        return {
            "drug": drug.name,
            "disrupted": True,
            "patients_at_risk": drug.patients_dependent,
            "drug_type": drug.drug_type.value
        }

    async def contaminate_drug(
        self,
        drug_id: str
    ) -> Dict[str, Any]:
        """Contaminate drug supply."""
        drug = self.drugs.get(drug_id)
        if not drug:
            return {"error": "Drug not found"}

        affected = drug.patients_dependent
        self.lives_at_risk += affected

        return {
            "drug": drug.name,
            "contaminated": True,
            "patients_affected": affected,
            "potential_deaths": int(affected * 0.2)
        }

    # =========================================================================
    # MEDICAL RECORDS
    # =========================================================================

    async def access_records(
        self,
        patient_id: str,
        conditions: List[str],
        medications: List[str]
    ) -> MedicalRecord:
        """Access medical records."""
        record = MedicalRecord(
            id=self._gen_id(),
            patient_id=patient_id,
            conditions=conditions,
            medications=medications,
            access_level="full"
        )

        self.records[record.id] = record

        return record

    async def compromise_records(
        self,
        record_id: str
    ) -> Dict[str, Any]:
        """Compromise medical records."""
        record = self.records.get(record_id)
        if not record:
            return {"error": "Record not found"}

        record.compromised = True
        self.records_compromised += 1

        return {
            "patient": record.patient_id,
            "compromised": True,
            "conditions_exposed": len(record.conditions),
            "medications_exposed": len(record.medications)
        }

    async def alter_records(
        self,
        record_id: str,
        alterations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Alter medical records."""
        record = self.records.get(record_id)
        if not record:
            return {"error": "Record not found"}

        if "conditions" in alterations:
            record.conditions = alterations["conditions"]
        if "medications" in alterations:
            record.medications = alterations["medications"]

        self.lives_at_risk += 1  # Wrong treatment could be fatal

        return {
            "patient": record.patient_id,
            "altered": True,
            "new_conditions": record.conditions,
            "new_medications": record.medications
        }

    # =========================================================================
    # PANDEMIC ENGINEERING
    # =========================================================================

    async def engineer_pathogen(
        self,
        name: str,
        transmission: str,
        mortality_rate: float,
        incubation_days: int
    ) -> Pathogen:
        """Engineer a pathogen."""
        pathogen = Pathogen(
            id=self._gen_id(),
            name=name,
            transmission=transmission,
            mortality_rate=mortality_rate,
            incubation_days=incubation_days
        )

        self.pathogens.append(pathogen)

        return pathogen

    async def release_pathogen(
        self,
        pathogen_id: str,
        population: int
    ) -> Dict[str, Any]:
        """Release pathogen."""
        pathogen = next((p for p in self.pathogens if p.id == pathogen_id), None)
        if not pathogen:
            return {"error": "Pathogen not found"}

        infected = int(population * random.uniform(0.1, 0.7))
        deaths = int(infected * pathogen.mortality_rate)

        self.lives_at_risk += deaths

        return {
            "pathogen": pathogen.name,
            "transmission": pathogen.transmission,
            "population": population,
            "projected_infected": infected,
            "projected_deaths": deaths,
            "incubation_days": pathogen.incubation_days
        }

    # =========================================================================
    # FULL MEDICAL DOMINATION
    # =========================================================================

    async def full_medical_domination(
        self,
        region: str
    ) -> Dict[str, Any]:
        """Execute full medical domination."""
        results = {
            "facilities_identified": 0,
            "facilities_controlled": 0,
            "devices_controlled": 0,
            "drugs_controlled": 0,
            "records_compromised": 0,
            "lives_at_risk": 0
        }

        # Identify and control facilities
        facility_types = [
            (FacilityType.HOSPITAL, 500),
            (FacilityType.HOSPITAL, 300),
            (FacilityType.EMERGENCY_CENTER, 50),
            (FacilityType.CLINIC, 20)
        ]

        for ft, beds in facility_types:
            facility = await self.identify_facility(
                f"{ft.value}_{region}",
                ft, beds, region
            )
            results["facilities_identified"] += 1

            control = await self.control_facility(facility.id, ControlMethod.NETWORK_INTRUSION)
            if control.get("success"):
                results["facilities_controlled"] += 1

                # Control devices in facility
                for dt in [DeviceType.PACEMAKER, DeviceType.VENTILATOR, DeviceType.INSULIN_PUMP]:
                    for i in range(random.randint(5, 20)):
                        device = await self.identify_device(dt, f"patient_{i}", facility.id)
                        dev_control = await self.control_device(device.id, ControlMethod.DEVICE_EXPLOIT)
                        if dev_control.get("success"):
                            results["devices_controlled"] += 1

        # Control drug supplies
        drug_types = [
            ("Insulin", DrugType.LIFE_SAVING, 10000),
            ("Blood_Thinner", DrugType.CHRONIC, 5000),
            ("Antibiotics", DrugType.ANTIBIOTIC, 8000),
            ("Chemo_Drug", DrugType.CHEMOTHERAPY, 500)
        ]

        for name, dt, patients in drug_types:
            drug = await self.track_drug_supply(name, dt, patients * 30, patients)
            control = await self.control_drug_supply(drug.id, ControlMethod.SUPPLY_CHAIN)
            if control.get("success"):
                results["drugs_controlled"] += 1

                # Disrupt some
                if random.random() < 0.3:
                    await self.disrupt_drug_supply(drug.id)

        # Compromise records
        for i in range(100):
            record = await self.access_records(
                f"patient_{i}",
                ["condition_1", "condition_2"],
                ["med_1", "med_2"]
            )
            await self.compromise_records(record.id)
            results["records_compromised"] += 1

        results["lives_at_risk"] = self.lives_at_risk

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "facilities_tracked": len(self.facilities),
            "facilities_controlled": self.facilities_controlled,
            "devices_tracked": len(self.devices),
            "devices_controlled": self.devices_controlled,
            "drugs_tracked": len(self.drugs),
            "drugs_controlled": self.drugs_controlled,
            "records_accessed": len(self.records),
            "records_compromised": self.records_compromised,
            "pathogens_engineered": len(self.pathogens),
            "lives_at_risk": self.lives_at_risk
        }


# ============================================================================
# SINGLETON
# ============================================================================

_controller: Optional[MedicalSystemsController] = None


def get_medical_controller() -> MedicalSystemsController:
    """Get the global medical controller."""
    global _controller
    if _controller is None:
        _controller = MedicalSystemsController()
    return _controller


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate medical control."""
    print("=" * 60)
    print("🏥 MEDICAL SYSTEMS CONTROLLER 🏥")
    print("=" * 60)

    controller = get_medical_controller()

    # Facility
    print("\n--- Facility Control ---")
    hospital = await controller.identify_facility(
        "Metro General Hospital",
        FacilityType.HOSPITAL,
        500,
        "Metro City"
    )
    print(f"Facility: {hospital.name}")
    print(f"Beds: {hospital.beds}")
    print(f"Patients: {hospital.patients}")
    print(f"Critical: {hospital.critical_patients}")

    control = await controller.control_facility(hospital.id, ControlMethod.NETWORK_INTRUSION)
    print(f"Control: {control}")

    # Device
    print("\n--- Device Control ---")
    device = await controller.identify_device(
        DeviceType.PACEMAKER,
        "patient_001",
        hospital.id
    )
    print(f"Device: {device.device_type.value}")

    dev_control = await controller.control_device(device.id, ControlMethod.DEVICE_EXPLOIT)
    print(f"Control: {dev_control}")

    manip = await controller.manipulate_device(device.id, "malfunction")
    print(f"Manipulation: {manip}")

    # Drug supply
    print("\n--- Drug Supply Control ---")
    drug = await controller.track_drug_supply(
        "Insulin",
        DrugType.LIFE_SAVING,
        100000,
        5000
    )
    print(f"Drug: {drug.name}")
    print(f"Patients dependent: {drug.patients_dependent}")

    drug_control = await controller.control_drug_supply(drug.id, ControlMethod.SUPPLY_CHAIN)
    print(f"Control: {drug_control}")

    disrupt = await controller.disrupt_drug_supply(drug.id)
    print(f"Disruption: {disrupt}")

    # Medical records
    print("\n--- Medical Records ---")
    record = await controller.access_records(
        "VIP_001",
        ["Diabetes", "Heart Disease"],
        ["Insulin", "Beta Blockers"]
    )
    print(f"Patient: {record.patient_id}")
    print(f"Conditions: {record.conditions}")

    compromise = await controller.compromise_records(record.id)
    print(f"Compromise: {compromise}")

    alter = await controller.alter_records(record.id, {
        "medications": ["Placebo", "Wrong Drug"]
    })
    print(f"Alteration: {alter}")

    # Pathogen
    print("\n--- Pandemic Engineering ---")
    pathogen = await controller.engineer_pathogen(
        "BAEL-V",
        "airborne",
        0.15,
        7
    )
    print(f"Pathogen: {pathogen.name}")
    print(f"Transmission: {pathogen.transmission}")
    print(f"Mortality: {pathogen.mortality_rate * 100}%")

    release = await controller.release_pathogen(pathogen.id, 1000000)
    print(f"Release: {release}")

    # Full domination
    print("\n--- FULL MEDICAL DOMINATION ---")
    domination = await controller.full_medical_domination("Target Region")
    for k, v in domination.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    # Stats
    print("\n--- CONTROLLER STATISTICS ---")
    stats = controller.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🏥 BA'EL DECIDES WHO LIVES AND DIES 🏥")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
