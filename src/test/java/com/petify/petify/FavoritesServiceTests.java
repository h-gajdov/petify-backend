package com.petify.petify;

import com.petify.petify.domain.Client;
import com.petify.petify.domain.Listing;
import com.petify.petify.domain.User;
import com.petify.petify.repo.ClientRepository;
import com.petify.petify.repo.FavoriteListingRepository;
import com.petify.petify.repo.ListingRepository;
import com.petify.petify.service.FavoritesService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;
import java.util.Optional;

import static org.mockito.Mockito.when;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.times;
import com.petify.petify.domain.FavoriteListing;

@ExtendWith(MockitoExtension.class)
public class FavoritesServiceTests {
    @Mock FavoriteListingRepository favoriteRepository;
    @Mock ClientRepository clientRepository;
    @Mock ListingRepository listingRepository;
    @InjectMocks
    FavoritesService service;

    @Test
    void getFavoritedListings_userIdNegative() {
        Long userId = -1L;
        when(favoriteRepository.findFavoritedListingDTOs(userId)).thenReturn(Collections.emptyList());

        service.getFavoritedListings(userId);

        verify(favoriteRepository).findFavoritedListingDTOs(userId);
    }

    @Test
    void getFavoritedListings_userIdZero() {
        Long userId = 0L;
        when(favoriteRepository.findFavoritedListingDTOs(userId)).thenReturn(Collections.emptyList());

        service.getFavoritedListings(userId);

        verify(favoriteRepository).findFavoritedListingDTOs(userId);
    }

    @Test
    void getFavoritedListings_userIdPositive() {
        Long userId = 1L;
        when(favoriteRepository.findFavoritedListingDTOs(userId)).thenReturn(Collections.emptyList());

        service.getFavoritedListings(userId);

        verify(favoriteRepository).findFavoritedListingDTOs(userId);
    }

    @Test
    void baseTest_bothValid() {
        Long validUserId = 1L;
        Long validListingId = 1L;

        Listing listing = listing(validListingId);
        Client client = client(validUserId);

        when(listingRepository.findById(validListingId)).thenReturn(Optional.of(listing));
        when(clientRepository.findByUserId(validUserId)).thenReturn(Optional.of(client));

        service.addFavorite(validUserId, validListingId);
        verify(favoriteRepository, times(1)).save(any(FavoriteListing.class));
    }

    @Test
    void addFavorite_userIdZero() {
        Long userId = 0L;
        Long listingId = 1L;

        when(clientRepository.findByUserId(userId)).thenReturn(Optional.empty());

        RuntimeException exception = assertThrows(RuntimeException.class,
                () -> service.addFavorite(userId, listingId));
        assertEquals("Client not found", exception.getMessage());
    }

    @Test
    void addFavorite_userIdNegative() {
        Long userId = -1L;
        Long listingId = 1L;

        when(clientRepository.findByUserId(userId)).thenReturn(Optional.empty());

        RuntimeException exception = assertThrows(RuntimeException.class,
                () -> service.addFavorite(userId, listingId));
        assertEquals("Client not found", exception.getMessage());
    }

    @Test
    void addFavorite_listingIdZero() {
        Long userId = 1L;
        Long listingId = 0L;

        Client client = client(userId);
        when(clientRepository.findByUserId(userId)).thenReturn(Optional.of(client));
        when(listingRepository.findById(listingId)).thenReturn(Optional.empty());

        RuntimeException exception = assertThrows(RuntimeException.class,
                () -> service.addFavorite(userId, listingId));
        assertEquals("Listing not found", exception.getMessage());
    }

    @Test
    void addFavorite_listingIdNegative() {
        Long userId = 1L;
        Long listingId = -1L;

        Client client = client(userId);
        when(clientRepository.findByUserId(userId)).thenReturn(Optional.of(client));
        when(listingRepository.findById(listingId)).thenReturn(Optional.empty());

        RuntimeException exception = assertThrows(RuntimeException.class,
                () -> service.addFavorite(userId, listingId));
        assertEquals("Listing not found", exception.getMessage());
    }


    private Listing listing(Long id) {
        Listing listing = new Listing();
        listing.setListingId(id);
        return listing;
    }

    private Client client(Long id) {
        Client client = new Client();
        client.setUser(new User());
        client.getUser().setUserId(id);
        return client;
    }
}
