package com.petify.petify.service;

import com.petify.petify.domain.Owner;
import com.petify.petify.domain.Pet;
import com.petify.petify.domain.User;
import com.petify.petify.dto.AnimalResponseDTO;
import com.petify.petify.dto.CreatePetRequest;
import com.petify.petify.repo.OwnerRepository;
import com.petify.petify.repo.PetRepository;
import com.petify.petify.repo.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PetServiceTest {

    @Mock
    private PetRepository petRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private OwnerRepository ownerRepository;

    @InjectMocks
    private PetService petService;

    @Test
    void addPetCreatesOwnerWhenUserIsNotAlreadyOwner() {
        User user = user(7L);
        Owner savedOwner = new Owner(user);
        savedOwner.setUserId(7L);
        CreatePetRequest request = validPetRequest();

        when(userRepository.findById(7L)).thenReturn(Optional.of(user));
        when(ownerRepository.findByUserId(7L)).thenReturn(Optional.empty());
        when(ownerRepository.save(any(Owner.class))).thenReturn(savedOwner);
        when(petRepository.save(any(Pet.class))).thenAnswer(invocation -> {
            Pet pet = invocation.getArgument(0);
            pet.setAnimalId(42L);
            return pet;
        });

        AnimalResponseDTO result = petService.addPet(7L, request);

        assertThat(result.getAnimalId()).isEqualTo(42L);
        assertThat(result.getName()).isEqualTo("Mila");
        assertThat(result.getOwnerUserId()).isEqualTo(7L);

        ArgumentCaptor<Owner> ownerCaptor = ArgumentCaptor.forClass(Owner.class);
        verify(ownerRepository).save(ownerCaptor.capture());
        assertThat(ownerCaptor.getValue().getUser()).isSameAs(user);

        ArgumentCaptor<Pet> petCaptor = ArgumentCaptor.forClass(Pet.class);
        verify(petRepository).save(petCaptor.capture());
        assertThat(petCaptor.getValue().getOwner()).isSameAs(savedOwner);
        assertThat(petCaptor.getValue().getSpecies()).isEqualTo("Dog");
    }

    @Test
    void addPetUsesExistingOwnerWithoutSavingANewOne() {
        User user = user(8L);
        Owner existingOwner = new Owner(user);
        existingOwner.setUserId(8L);
        CreatePetRequest request = validPetRequest();

        when(userRepository.findById(8L)).thenReturn(Optional.of(user));
        when(ownerRepository.findByUserId(8L)).thenReturn(Optional.of(existingOwner));
        when(petRepository.save(any(Pet.class))).thenAnswer(invocation -> invocation.getArgument(0));

        AnimalResponseDTO result = petService.addPet(8L, request);

        assertThat(result.getOwnerUserId()).isEqualTo(8L);
        verify(ownerRepository, never()).save(any(Owner.class));
        verify(petRepository).save(any(Pet.class));
    }

    @Test
    void addPetRejectsBlankNameBeforeCallingRepositories() {
        CreatePetRequest request = validPetRequest();
        request.setName(" ");

        assertThatThrownBy(() -> petService.addPet(7L, request))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("Pet name is required");

        verify(userRepository, never()).findById(any());
        verify(ownerRepository, never()).findByUserId(any());
        verify(petRepository, never()).save(any());
    }

    @Test
    void getPetByIdReturnsPetDetails() {
        User user = user(3L);
        Owner owner = new Owner(user);
        owner.setUserId(3L);
        Pet pet = new Pet("Luna", "F", LocalDate.of(2022, 4, 5), null, "Cat", "Cat", "Siamese", "Skopje", owner);
        pet.setAnimalId(99L);

        when(petRepository.findById(99L)).thenReturn(Optional.of(pet));

        AnimalResponseDTO result = petService.getPetById(99L);

        assertThat(result.getAnimalId()).isEqualTo(99L);
        assertThat(result.getName()).isEqualTo("Luna");
        assertThat(result.getOwnerUserId()).isEqualTo(3L);
    }

    private static CreatePetRequest validPetRequest() {
        return new CreatePetRequest(
            "Mila",
            "F",
            LocalDate.of(2021, 2, 3),
            null,
            "Mammal",
            "Dog",
            "Labrador",
            "Skopje"
        );
    }

    private static User user(Long id) {
        User user = new User("user" + id, "user" + id + "@petify.test", "secret", "Test", "User");
        user.setUserId(id);
        return user;
    }
}
