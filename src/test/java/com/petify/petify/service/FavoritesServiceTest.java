package com.petify.petify.service;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import static org.mockito.ArgumentMatchers.any;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import org.mockito.junit.jupiter.MockitoExtension;

import com.petify.petify.domain.Client;
import com.petify.petify.domain.FavoriteListing;
import com.petify.petify.domain.Listing;
import com.petify.petify.domain.User;
import com.petify.petify.repo.ClientRepository;
import com.petify.petify.repo.FavoriteListingRepository;
import com.petify.petify.repo.ListingRepository;

@ExtendWith(MockitoExtension.class)
class FavoritesServiceTest {

    @Mock
    private FavoriteListingRepository favoriteRepository;

    @Mock
    private ClientRepository clientRepository;

    @Mock
    private ListingRepository listingRepository;

    @InjectMocks
    private FavoritesService favoritesService;

    @Test
    void addFavoriteSavesFavoriteForClientAndListing() {
        Client client = client(11L);
        Listing listing = listing(22L);

        when(clientRepository.findByUserId(11L)).thenReturn(Optional.of(client));
        when(listingRepository.findById(22L)).thenReturn(Optional.of(listing));

        favoritesService.addFavorite(11L, 22L);

        ArgumentCaptor<FavoriteListing> captor = ArgumentCaptor.forClass(FavoriteListing.class);
        verify(favoriteRepository).save(captor.capture());
        assertThat(captor.getValue().getClient()).isSameAs(client);
        assertThat(captor.getValue().getListing()).isSameAs(listing);
    }

    @Test
    void removeFavoriteDeletesExistingFavorite() {
        Client client = client(11L);
        Listing listing = listing(22L);
        FavoriteListing favorite = new FavoriteListing(client, listing);

        when(clientRepository.findByUserId(11L)).thenReturn(Optional.of(client));
        when(listingRepository.findById(22L)).thenReturn(Optional.of(listing));
        when(favoriteRepository.findByClientAndListing(client, listing)).thenReturn(Optional.of(favorite));

        favoritesService.removeFavorite(11L, 22L);

        verify(favoriteRepository).delete(favorite);
    }

    @Test
    void removeFavoriteThrowsWhenFavoriteDoesNotExist() {
        Client client = client(11L);
        Listing listing = listing(22L);

        when(clientRepository.findByUserId(11L)).thenReturn(Optional.of(client));
        when(listingRepository.findById(22L)).thenReturn(Optional.of(listing));
        when(favoriteRepository.findByClientAndListing(client, listing)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> favoritesService.removeFavorite(11L, 22L))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("Favorite not found");

        verify(favoriteRepository, never()).delete(any());
    }

    @Test
    void isFavoritedReturnsFalseWithoutListingLookupWhenClientDoesNotExist() {
        when(clientRepository.findByUserId(11L)).thenReturn(Optional.empty());

        boolean favorited = favoritesService.isFavorited(11L, 22L);

        assertThat(favorited).isFalse();
        verify(listingRepository, never()).findById(any());
        verify(favoriteRepository, never()).findByClientAndListing(any(), any());
    }

    @Test
    void isFavoritedReturnsTrueWhenFavoriteExists() {
        Client client = client(11L);
        Listing listing = listing(22L);

        when(clientRepository.findByUserId(11L)).thenReturn(Optional.of(client));
        when(listingRepository.findById(22L)).thenReturn(Optional.of(listing));
        when(favoriteRepository.findByClientAndListing(client, listing))
            .thenReturn(Optional.of(new FavoriteListing(client, listing)));

        assertThat(favoritesService.isFavorited(11L, 22L)).isTrue();
    }

    private static Client client(Long userId) {
        User user = new User("client" + userId, "client" + userId + "@petify.test", "secret", "Test", "Client");
        user.setUserId(userId);
        return new Client(user);
    }

    private static Listing listing(Long listingId) {
        Listing listing = new Listing();
        listing.setListingId(listingId);
        return listing;
    }
}
